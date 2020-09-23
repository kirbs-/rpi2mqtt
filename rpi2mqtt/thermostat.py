from rpi2mqtt.switch import Switch
from rpi2mqtt.base import Sensor
from rpi2mqtt.temperature import BME280
import RPi.GPIO as GPIO


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


class HestiaPi(Sensor):

    def __init__(self, name, topic):
        # self.modes = HVAC.HEAT_PUMP_MODES
        super(HestiaPi, self).__init__(name, None, topic, 'climate', 'HestiaPi')
        self.mode = 'off'
        self.active_mode = 'off'
        self.set_point_cool = 75
        self.set_point_heat = 70
        # Minimum time HVAC should run
        self.min_run_time = 15
        # how soon can HVAC be activated again after stopping
        self.min_trigger_cooldown_time = 15
        self.bme280 = None
        self.modes = {}

    def setup(self):
        self.bme280 = BME280(self.name, self.topic)

        for mode, pins in HVAC.HEAT_PUMP_MODES.items():
            switch = Switch(self.name, pins, '{}_{}'.format(self.topic, mode), mode)
            switch.setup()
            self.modes[mode] = switch

    def set_state(self, mode, state):
        if state == 'ON':
            self.modes[mode].on()
        elif state == 'OFF':
            self.modes[mode].off()
        else:
            raise IllegalArgumentError("Fan state '{}' is not a valid state.".format(state))

    def state(self):
        data = self.bme280.state()


    