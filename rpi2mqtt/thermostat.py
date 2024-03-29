from rpi2mqtt.switch import BasicSwitch, Switch
from rpi2mqtt.base import Sensor
from rpi2mqtt.mqtt import MQTT
from rpi2mqtt.temperature import BME280
from rpi2mqtt.config import Config
import RPi.GPIO as GPIO
import pendulum
import logging
import json
import rpi2mqtt.math as math
import time
from collections import deque


class HVAC(object):
    HEAT_PUMP = {
        'fan': 18,
        'compressor': 23,
        'reversing_valve': 12,
        'aux': 16,
    }

    HEAT_PUMP_MODES = {
        'off': [],
        'fan': [HEAT_PUMP['fan']],
        'heat': [HEAT_PUMP['fan'], HEAT_PUMP['compressor']],
        '_cool': [HEAT_PUMP['reversing_valve']],
        'cool': [HEAT_PUMP['fan'], HEAT_PUMP['compressor'], HEAT_PUMP['reversing_valve']],
        'aux': [HEAT_PUMP['fan'], HEAT_PUMP['compressor'], HEAT_PUMP['aux']],
        'boost': [HEAT_PUMP['aux']],
        'emergency': [HEAT_PUMP['fan'], HEAT_PUMP['aux']],
    }

    # ON = 'ON'
    # OFF = 'OFF'

    HEAT = 'heat'
    COOL = 'cool'
    AUX = 'aux'
    EMERGENCY = 'emergency'
    BOOST = 'boost'
    FAN = 'fan'
    FAN_ON = 'high'
    AUTO = 'auto'
    ON = 'on'
    OFF = 'off'


class HvacException(Exception):
    pass


class HestiaPi(Sensor):

    def __init__(self, **kwargs):
        # self._modes = HVAC.HEAT_PUMP_MODES
        super(HestiaPi, self).__init__(kwargs.get('name'), None, kwargs.get('topic'), 'climate', 'HestiaPi')
        self.mode = kwargs.get('mode', 'heat')
        # self.active = False
        # self.desired_mode = 'off'
        self.active_start_time = None
        self.cool_setpoint = kwargs.get('cool_setpoint', 76)
        self.heat_setpoint = kwargs.get('heat_setpoint', 68)
        # how much wiggle room in temperature reading before starting/stopping HVAC.
        # setting this too low can trigger frequence HVAC cycles.
        self.set_point_tolerance = kwargs.get('set_point_tolerance', 0.5)
        # Minimum time HVAC should run (in minutes)
        self.min_run_time = kwargs.get('min_run_time', 15)
        # how soon can HVAC be activated again after stopping (in minutes)
        self.min_trigger_cooldown_time = kwargs.get('min_trigger_cooldown_time', 15)
        self.last_mode_change_time = None
        self.last_hvac_state_change_time = None
        self._bme280 = None
        # container to holder mode switches. Do not use directly.
        self._modes = {}
        # container to store temperature history
        self._temperature_history = deque(maxlen=kwargs.get('temperature_history_period', 6))
        # Minimum temperature rate of change over 4 measurements
        self.minimum_temp_rate_of_change = kwargs.get('minimum_temp_rate_of_change', -0.25)
        # super(HestiaPi, self).__init__(name, None, topic, 'climate', 'HestiaPi')
        # put thermostat into test mode. i.e. don't trigger HVAC commands
        self.dry_run = kwargs.get('dry_run')
        # save boost state
        self._boosting_heat = HVAC.OFF
        self._boosting_start_time = None
        self._boosting_enabled_switch = None
        self.aux_enabled = kwargs.get('aux_enabled', HVAC.ON)

        self.setup()

    def setup(self):
        logging.debug('Setting up HestiaPi')
        self._bme280 = BME280(self.name, self.topic)
        self._boosting_enabled_switch = HVACAuxSwitch(self)

        for mode, pins in HVAC.HEAT_PUMP_MODES.items():
            switch = BasicSwitch(self.name, pins, '{}_{}'.format(self.topic, mode), mode)
            # switch.setup()
            self._modes[mode] = switch

        # setup GPIO inputs on HVAC pins
        GPIO.setmode(GPIO.BCM)
        for capability, pin in HVAC.HEAT_PUMP.items():
            GPIO.setup(pin, GPIO.IN)

        # Subscribe to MQTT command topics
        MQTT.subscribe(self.mode_command_topic, self.mqtt_set_mode_callback)
        MQTT.subscribe(self.temperature_set_point_command_topic, self.mqtt_set_temperature_set_point_callback)
        MQTT.subscribe(self.fan_command_topic, self.mqtt_set_fan_state_callback)
        MQTT.subscribe(self.aux_command_topic, self.mqtt_set_aux_mode_callback)

    @property
    def mode_command_topic(self):
        return '{}/mode/set'.format(self.topic)

    @property
    def temperature_set_point_command_topic(self):
        return '{}/temperature/set'.format(self.topic)

    @property
    def fan_command_topic(self):
        return '{}/fan/set'.format(self.topic)

    @property
    def  aux_command_topic(self):
        return '{}/aux/set'.format(self.topic)

    @property
    def homeassistant_mqtt_config_topic(self):
        return 'homeassistant/{}/{}/config'.format('climate', self.name)

    @property
    def homeassistant_mqtt_config(self):
        return {
                'name': '{}_{}'.format(self.name, self.device_class),
                'unique_id': '{}_{}_{}_rpi2mqtt'.format(self.name, self.device_model, self.device_class),
                "json_attributes_topic": self.topic,
                'device': self.device_config,
                'min_temp': 65,
                'max_temp': 80,
                'initial': 72,
                'modes': ['off', 'auto', 'heat', 'cool', 'aux'],
                'fan_modes': ['auto','high'],
                'action_topic': self.topic,
                'action_template': '{{ value_json.hvac_state }}',
                'current_temperature_topic': self.topic,
                'current_temperature_template': '{{ value_json.current_temperature | round(1) }}',
                'mode_state_topic': self.topic,
                'mode_state_template': '{{ value_json.mode }}',
                'mode_command_topic': self.mode_command_topic, 
                'temperature_state_topic': self.topic,
                'temperature_state_template': '{{ value_json.set_point }}',
                'temperature_command_topic': self.temperature_set_point_command_topic,
                'aux_state_topic': self.topic,
                'aux_state_topic': '{{ value_json.aux_mode }}', # TODO refactor aux_mode to aux_state
                'aux_command_topic': self.aux_command_topic,
                'fan_modes': ['auto', 'high'],
                'fan_mode_state_topic': self.topic,
                'fan_mode_state_template': '{{ value_json.fan_state }}',
                'fan_mode_command_topic': self.fan_command_topic
            }

    def set_state(self, mode, state):
        if not self.dry_run:
            if state == HVAC.ON:
                if mode not in [HVAC.FAN, HVAC.BOOST]:
                    self.active_start_time = pendulum.now()

                if mode == HVAC.COOL:
                    self._modes['heat'].on()
                    # delay reversing valve turn on before cooling starts
                    time.sleep(15)
                    self._modes['_cool'].on()
                else:
                    self._modes[mode].on()
                    
                # confirm mode change
                if mode == self.hvac_state: # TODO if boosting then only check boosting pin is active
                    logging.debug('Turned {} {}.'.format(mode, state))
                else:
                    logging.warn('Did not set HVAC state to {}. Try again.'.format(mode))

            elif state == HVAC.OFF:
                self._modes[mode].off()
                
                # if mode == HVAC.COOL:
                #     time.sleep(3)
                #     self._modes['_cool'].off()

                if mode not in [HVAC.FAN, HVAC.BOOST]:
                    self.active_start_time = None
                    self._temperature_history = []

                # confirm mode change
                if 'off' == self.hvac_state:
                    logging.debug('Turned {} {}.'.format(mode, state))
                else:
                    logging.warn('Did not set HVAC state to {}. Try again.'.format(mode))
            else:
                raise HvacException("State '{}' is not a valid state.".format(state))
        if mode not in [HVAC.FAN, HVAC.BOOST]:
            self.last_hvac_state_change_time = pendulum.now()

    @property
    def active_time(self):
        if self.active:
            try:
                return (pendulum.now() - self.active_start_time).in_minutes() 
            except Exception as e:
                logging.exception(e)
        return 0

    @property
    def boosting_active_time(self):
        if self._boosting_heat == HVAC.ON:
            try:
                return (pendulum.now() - self._boosting_start_time).in_minutes() 
            except Exception as e:
                logging.exception(e)
        return 0

    @property
    def active(self):
        return self.hvac_state in  [HVAC.COOL, HVAC.HEAT, HVAC.AUX]

    @property
    def minutes_since_last_mode_change(self):
        # if self.active:
        if self.last_mode_change_time:
            _minutes = (pendulum.now() - self.last_mode_change_time).in_minutes() 
            logging.info(f'{_minutes} minutes since last mode change.')
            return _minutes
        else:
            return 1000

    @property
    def minutes_since_last_hvac_state_change(self):
        if self.last_hvac_state_change_time:
            return (pendulum.now() - self.last_hvac_state_change_time).in_minutes() 
        else:
            return 1000

    @property
    def set_point(self):
        if self.mode == HVAC.HEAT:
            return self.heat_setpoint
        elif self.mode == HVAC.COOL:
            return self.cool_setpoint

    @property
    def hvac_state(self):
        """Current HVAC mode based on active GPIO pins."""
        active_pins = []
        # read pin state
        for capability, pin in HVAC.HEAT_PUMP.items():
            if GPIO.input(pin):
                active_pins.append(pin)
        active_pins = set(active_pins)

        # search heat pump modes for a match
        for mode, p in HVAC.HEAT_PUMP_MODES.items():
            if active_pins == set(p):
                logging.debug('HVAC state is "{}". Active GPIO pins = {}'.format(mode, active_pins))
                return mode

    @property
    def fan_state(self):
        if self.hvac_state == HVAC.FAN:
            return HVAC.FAN_ON
        else:
            return HVAC.AUTO

    @property
    def ha_hvac_state(self):
        state = self.hvac_state
        if state in ['heat','cool']:
            return '{}ing'.format(state)
        elif state == HVAC.AUX:
            return 'heating'
        else:
            return state

    @property
    def current_temperature(self):
        return round(self.temperature)

    @property
    def temperature(self):
        return self._bme280.state()['temperature']

    def append_tempearture_history(self):
        """Save current temperature in _temperature history and maintain N readings."""
         # if system is active log temperature changes for analysis
        # if self.active:
        self._temperature_history.append(self.temperature)
        logging.debug('Temperature history = {}'.format(self._temperature_history))
        # if len(self.temperature_history) > 6: # how many readings should we keep track of. 4 is ~20 minutes.
        #     self.temperature_history.pop(0)

    @property
    def temperature_rate_of_change(self):
        if len(self._temperature_history) > 1:
            roc = math.rate_of_change(self._temperature_history)
            logging.debug('Temperature rate of change is {}.'.format(roc))
            return roc

    def state(self):
        data = self._bme280.state()
        # aux_enabled_state = self._boosting_enabled_switch.state()
        return {
            'bme280': data,
            'mode': self.mode,
            'aux_enabled': self.aux_enabled,
            'aux_mode': self._boosting_heat,
            'active_time': self.active_time,
            'aux_active_time': self.boosting_active_time,
            'active': self.active,
            'hvac_state': self.ha_hvac_state,
            'fan_state': self.fan_state,
            'heat_setpoint': self.heat_setpoint,
            'cool_setpoint': self.cool_setpoint,
            'set_point': self.set_point,
            'current_temperature': self.current_temperature,
            'humidity': self._bme280.state()['humidity'],
            'pressure': self._bme280.state()['pressure'],
        }

    def payload(self):
        return json.dumps(self.state())

    def callback(self, **kwargs):
        # system active, should we turn it off?
        logging.info('Checking temperature...temp = {}, heat_setpoint = {}, cool_setpoint = {}, set_point_tolerance = {}'.format(self.temperature, self.heat_setpoint, self.cool_setpoint, self.set_point_tolerance))
        self.append_tempearture_history()
        
        if self.active and self.mode == HVAC.OFF:
            logging.info('Mode is off, but system is active. Turning HVAC off')
            self.off()

            # reset mode to normal heat
            if self._boosting_heat:
                self.boost_heat(HVAC.OFF)

        elif self.active:
            if self.mode in ['heat', 'aux'] and self.temperature > self.heat_setpoint + self.set_point_tolerance:
                # turn hvac off
                logging.info('Temperature is {}. Turning heat off.'.format(self.temperature))
                self.off()

                # reset mode to normal heat
                if self._boosting_heat:
                    self.boost_heat(HVAC.OFF)

            elif self.mode == 'cool' and self.temperature < self.cool_setpoint - self.set_point_tolerance:
                # turn hvac off
                logging.info('Temperature is {}. Turning cool off.'.format(self.temperature))
                self.off()

            # should system boost heating with aux heat?
            logging.debug("Checking temperature rate of change...current rate = {}, min rate = {}".format(self.temperature_rate_of_change, self.minimum_temp_rate_of_change))
            if self.mode == HVAC.HEAT and self.temperature_rate_of_change and self.temperature_rate_of_change <= self.minimum_temp_rate_of_change:
                self.boost_heat(HVAC.ON)

        else:
            if self.mode == 'heat' and self.temperature < self.heat_setpoint - self.set_point_tolerance:
                # turn hvac on
                logging.info('Temperature is {}. Turning heat on.'.format(self.temperature))
                self.on()
            elif self.mode == 'cool' and self.temperature > self.cool_setpoint + self.set_point_tolerance:
                # turn hvac on
                logging.info('Temperature is {}. Turning cool on.'.format(self.temperature))
                self.on()
            # system is inactive, should we turn it on?
        # logging.info('HVAC is {}. Mode is {}. Temperature is {}.'.format(self.active, self.mode, self.temperature))
        MQTT.publish(self.topic, self.payload())

    # def mode_is_changeable(self):
    #     """Can thermostat active mode be chagned?"""
    #     # stop changes from cooling to heat or vice versa while system is running

    #     minutes_since_last_mode_change = (pendulum.now - self.last_mode_change_time).in_minutes()
    #     return not self.active and self.active_time >= self.min_run_time and self.minutes_since_last_mode_chage >= self.min_trigger_cooldown_time

    def set_mode(self, mode):
        logging.info('Changing mode to {}.'.format(mode))
        if mode in HVAC.HEAT_PUMP_MODES:
            self.mode = mode
            self.last_mode_change_time = pendulum.now()
            # Config.save()
        else:
            raise HvacException('{} mode is not a valid HVAC mode'.format(mode))

    def _can_change_hvac_state(self):
        """Don't change HVAC state from heat to cool or vice versa if the system is running."""
        if (self.hvac_state == 'cool' and self.mode == 'heat') or (self.hvac_state == 'heat' and self.mode == 'cool'): 
            logging.warn("Don't change between heating and cooling. Doing so may damage your system.")
        elif self.active and self.active_time <= self.min_run_time:
            logging.warn("System needs to run for atleast {} minutes. Only running for {} minutes.".format(self.min_run_time, self.active_time))
        elif not self.active and self.minutes_since_last_hvac_state_change <= self.min_run_time:
            logging.warn("System needs to idle for atleast {} minutes. Only idle for {} minutes.".format(self.min_run_time, self.minutes_since_last_hvac_state_change))
        elif self.minutes_since_last_mode_change <= self.min_trigger_cooldown_time:
            logging.warn("Can only change mode every {} minutes. It's been {} minutes since last change.".format(self.min_trigger_cooldown_time, self.minutes_since_last_mode_change))
        # elif self.mode == self.hvac_state:
        #     logging.info('Ignoring mode change since HVAC is alread in {} mode'.format(self.mode))
        else:
            return True

    def on(self):
        """Helper to turn HVAC and capture useful logging."""
        if self._can_change_hvac_state():
            self.set_state(self.mode, HVAC.ON)
            # TODO verify state was changed and publish result to MQTT
        else:
            logging.warn('Did not activate {}'.format(self.mode))

    def off(self):
        if self._can_change_hvac_state():
            self.set_state(self.mode, HVAC.OFF)
            self._temperature_history = []
        else:
            logging.warn("Did not deactivate {}.".format(self.mode))

    def fan_on(self):
        self.set_state(HVAC.FAN, HVAC.ON)
        logging.info('Turned fan on.')

    def fan_off(self):
        self.set_state(HVAC.FAN, HVAC.OFF)
        logging.info('Turned fan off.')

    def heat_boost_on(self):
        self.set_state(HVAC.BOOST, HVAC.ON)
        self._boosting_heat = HVAC.ON
        logging.info('Heat boost activated.')

    def heat_boost_off(self):
        self.set_state(HVAC.BOOST, HVAC.OFF)
        self._boosting_heat = HVAC.OFF
        logging.info('Heat boost deactivated.')

    def set_fan_mode(self, fan_mode):
        logging.info('Setting fan mode to {}.'.format(fan_mode))
        if fan_mode == HVAC.FAN_ON:
            self.fan_on()
        else:
            self.fan_off()

    def boost_heat(self, boost):
        # manually switching to AUX heat since we don't want to trigger state or mode safety checks.
        # self.mode = HVAC.AUX
        if self._boosting_enabled_switch.state == HVAC.ON:
            if boost == HVAC.ON:
                self.heat_boost_on()
                self._boosting_start_time = pendulum.now()
                # self._boosting_heat = HVAC.ON
            elif boost == HVAC.OFF:
                self.heat_boost_off()
                # reset boost metadata
                self._boosting_start_time = None
                # self.temperature_history = []
                # self._boosting_heat = HVAC.OFF
            else:
                raise HvacException('{} is not a valid boost value. allowed values are [[{},{}]'.format(boost, HVAC.ON, HVAC.OFF))
        # self._boosting_heat = boost
        else:
            logging.info("Boosting disabled by switch.")
    
    def mqtt_ping(self, topic, callback):
        logging.debug("Checing subcription status on topic {}".format(topic))
        response = MQTT.publish(topic, "ping")
        if response != 'pong':
            logging.warn("Not subscribed to topic {}. Resubscribing...".format(topic))
            MQTT.subscribe(topic, callback)

    """
    MQTT subscription callbacks
    """
    @MQTT.pongable
    def mqtt_set_temperature_set_point_callback(self, client, userdata, message):
        try:
            payload = message.payload.decode()
            logging.info("Received temperature set point update request: {}".format(message.payload))
            payload = float(payload)
            if self.mode == HVAC.HEAT:
                self.heat_setpoint = payload
            else:
                self.cool_setpoint = payload
            Config.save(sensor=self)
        except Exception as e:
            logging.error('Unable to proces message.', e)

        MQTT.publish(self.topic, self.payload())

    @MQTT.pongable
    def mqtt_set_fan_state_callback(self, client, userdata, message):
        try:
            payload = message.payload.decode().lower()
            logging.info("Received fand mode update request: {}".format(payload))
            self.set_fan_mode(payload)
            Config.save(sensor=self)
        except Exception as e:
            logging.error('Unable to proces message.', e)

        MQTT.publish(self.topic, self.payload())

    @MQTT.pongable
    def mqtt_set_mode_callback(self, client, userdata, message):
        try:
            payload = message.payload.decode().lower()
            logging.info("Received HVAC mode update request: {}".format(payload))
            self.set_mode(payload)
            Config.save(sensor=self)
        except Exception as e:
            logging.error('Unable to proces message.', e)

        MQTT.publish(self.topic, self.payload())

    @MQTT.pongable
    def mqtt_set_aux_mode_callback(self, client, userdata, message):
        try:
            payload = message.payload.decode().lower()
            logging.info("Received aux mode update request: {}".format(payload))
            self.boost_heat(payload)
            Config.save(sensor=self)
        except Exception as e:
            logging.error('Unable to proces message.', e)

        MQTT.publish(self.topic, self.payload())


class HVACAuxSwitch(Switch):

    def __init__(self, thermostat):
        super().__init__(thermostat.name, thermostat.pin, thermostat.topic, 'switch', 'generic_switch')
        self.thermostat = thermostat
        # self.power_state = thermostat.aux_enabled

    @property
    def homeassistant_mqtt_config(self):
        config = super(HVACAuxSwitch, self).homeassistant_mqtt_config
        config['value_template'] = "{{ value_json.aux_enabled }}"
        return config

    def setup(self, lazy_setup=True):
        # don't need any setup
        MQTT.subscribe(self.homeassistant_mqtt_config['command_topic'], self.mqtt_callback)

    def setup_output(self):
        # don't need to setup GPIO
        pass

    def on(self):
        self.thermostat.aux_enabled = HVAC.ON

    def off(self):
        self.thermostat.aux_enabled = HVAC.OFF

    def state(self):
        self.thermostat.aux_enabled

    def payload(self):
        return self.thermostat.payload()
    