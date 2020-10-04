from rpi2mqtt.switch import Switch
from rpi2mqtt.base import Sensor
import rpi2mqtt.mqtt as mqtt
from rpi2mqtt.temperature import BME280
import RPi.GPIO as GPIO
import pendulum
import logging





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
        'cool': [HEAT_PUMP['fan'], HEAT_PUMP['compressor'], HEAT_PUMP['reversing_valve']],
        'aux': [HEAT_PUMP['fan'], HEAT_PUMP['compressor'], HEAT_PUMP['aux']],
    }

    ON = 'ON'
    OFF = 'OFF'


class HvacException(Exception):
    pass

class HestiaPi(Sensor):

    def __init__(self, name, topic, heat_setpoint, cool_setpoint, set_point_tolerance=1.0, min_run_time=15):
        # self._modes = HVAC.HEAT_PUMP_MODES
        # super(HestiaPi, self).__init__(name, None, topic, 'climate', 'HestiaPi')
        self.mode = 'heat'
        # self.active = False
        # self.desired_mode = 'off'
        self.active_start_time = None
        self.set_point_cool = cool_setpoint
        self.set_point_heat = heat_setpoint
        # how much wiggle room in temperature reading before starting/stopping HVAC.
        # setting this too low can trigger frequence HVAC cycles.
        self.set_point_tolerance = set_point_tolerance
        # Minimum time HVAC should run (in minutes)
        self.min_run_time = min_run_time
        # how soon can HVAC be activated again after stopping (in minutes)
        self.min_trigger_cooldown_time = 15
        self.last_mode_change_time = None
        self.bme280 = None
        # container to holder mode switches. Do not use directly.
        self._modes = {}
        super(HestiaPi, self).__init__(name, None, topic, 'climate', 'HestiaPi')
        # self.setup()

    def setup(self):
        self.bme280 = BME280(self.name, self.topic)

        for mode, pins in HVAC.HEAT_PUMP_MODES.items():
            switch = Switch(self.name, pins, '{}_{}'.format(self.topic, mode), mode)
            # switch.setup()
            self._modes[mode] = switch

        # setup GPIO inputs on HVAC pins
        GPIO.setmode(GPIO.BCM)
        for capability, pin in HVAC.HEAT_PUMP.items():
            GPIO.setup(pin, GPIO.IN)

    def set_state(self, mode, state):
        if state == HVAC.ON:
            self.active_start_time = pendulum.now()
            self._modes[mode].on()
        elif state == HVAC.OFF:
            self._modes[mode].off()
            self.active_start_time = None
        else:
            raise HvacException("Fan state '{}' is not a valid state.".format(state))
        logging.info('Turned {} {}}.'.format(mode), state)

        # confirm mode change
        if mode == self.hvac_state:
            logging.info('Turned {} {}}.'.format(mode), state)
        else:
            logging.warn('Did not set mode to {}. Try again.'.format(mode))

    @property
    def active_time(self):
        if self.active:
            try:
                return (pendulum.now() - self.active_start_time).in_minutes() 
            except Exception as e:
                logging.exception(e)

    @property
    def active(self):
        return self.hvac_state in  ['cool','heat','aux']

    @property
    def minutes_since_last_mode_change(self):
        if self.active:
            return (pendulum.now - self.last_mode_change_time).in_minutes() 

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
                logging.debug('HVAC mode is "{}". Active GPIO pins = {}'.format(mode, active_pins))
                return mode

    @property
    def temperature(self):
        temp = self.bme280.state()['temperature']
        return temp * 1.8 + 32

    def state(self):
        data = self.bme280.state()
        return {
            'bme280': data,
            'mode': self.mode,
            'active_time': self.active_time,
            'hvac_state': self.hvac_state,
            'heat_setpoint': self.set_point_heat,
            'cool_setpoint': self.set_point_cool,
        }

    def callback(self, *args):
        # system active, should we turn it off?
        logging.debug('Checking temperature...temp = {}, heat_setpoint = {}, cool_setpoint = {}, set_point_tolerance = {}'.format(self.temperature, self.set_point_heat, self.set_point_cool, self.set_point_tolerance))
        if self.active:
            # if heating is current temperature above set point?
            if self.mode == 'heat' and self.temperature > self.set_point_heat + self.set_point_tolerance:
                # turn hvac off
                logging.info('Temperature is {}. Turning heat off.'.format(self.temperature))
                self.off()
            elif self.mode == 'cool' and self.temperature < self.set_point_cool - self.set_point_tolerance:
                # turn hvac off
                logging.info('Temperature is {}. Turning cool off.'.format(self.temperature))
                self.off()
            else:
                logging.warn('HVAC is active, but something is wrong. Mode is {}. Temperature is {}.'.format(self.mode, self.temperature))
        else:
            if self.mode == 'heat' and self.temperature < self.set_point_heat - self.set_point_tolerance:
                # turn hvac on
                logging.info('Temperature is {}. Turning heat on.'.format(self.temperature))
                self.on()
            elif self.mode == 'cool' and self.temperature > self.set_point_cool + self.set_point_tolerance:
                # turn hvac on
                logging.info('Temperature is {}. Turning cool on.'.format(self.temperature))
                self.on()
            else:
                logging.warn('HVAC is inactive, but something is wrong. Mode is {}. Temperature is {}.'.format(self.mode, self.temperature))
            # system is inactive, should we turn it on?

        mqtt.publish(self.topic, self.payload())

    # def mode_is_changeable(self):
    #     """Can thermostat active mode be chagned?"""
    #     # stop changes from cooling to heat or vice versa while system is running

    #     minutes_since_last_mode_change = (pendulum.now - self.last_mode_change_time).in_minutes()
    #     return not self.active and self.active_time >= self.min_run_time and self.minutes_since_last_mode_chage >= self.min_trigger_cooldown_time


    def mode(self, mode):
        if mode in HVAC.HEAT_PUMP_MODES:
            self.mode = mode
        else:
            raise IllegalArgumentException('{} mode is not a valid HVAC mode'.format(mode))

    def _can_change_hvac_state(self):
        """Don't change HVAC state from heat to cool or vice versa if the system is running."""
        if (self.hvac_state == 'cool' and self.mode == 'heat') or (self.hvac_state == 'heat' and self.mode == 'cool'): 
            logging.warn("Don't change between heating and cooling. May damage your system.")
        elif self.active_time <= self.min_run_time:
            logging.warn("System needs to run for atleast {} minutes. Only running for {} minutes.".format(self.min_run_time, self.active_time))
        elif self.minutes_since_last_mode_chage <= self.min_trigger_cooldown_time:
            logging.warn("Can only change mode every {} minutes. It's been {} minutes since last change.".format(self.min_trigger_cooldown_time, self.minutes_since_last_mode_change))
        elif self.mode == self.hvac_state:
            logging.info('Ignoring mode change since HVAC is alread in {} mode'.format(self.mode))
        else:
            return True

    def on(self):
        """Helper to turn HVAC and capture useful logging."""
        if self._can_change_hvac_state():
            self.set_state(self.mode, HVAC.ON)
            # TODO verify state was changed and publish result to MQTT
        else:
            logging.warn('HVAC already {}ing in {} mode'.format(self.mode, self.mode))

    def off(self):
        if self._can_change_hvac_state():
            self.set_state(self.mode, HVAC.OFF)

        else:
            logging.warn("Did not activate HVAC.")





    