import RPi.GPIO as GPIO
from rpi2mqtt.base import Sensor
from rpi2mqtt.mqtt import MQTT as mqtt
import json
import logging


class ReedSwitch(Sensor):
    """
    Extends simple binary sensor by adding configuration for normally open or normally closed reed switches.
    """

    def __init__(self, name, pin, topic, normally_open, device_class=None):
        super(ReedSwitch, self).__init__(name, pin, topic, device_class, 'reed_switch')
        self.normally_open = normally_open
        self.setup()

    def setup(self):
        """
        Setup GPIO pin to read input value.
        :return: None
        """
        # device_config = {'name': self.name,
        #                  'identifiers': self.name,
        #                  'sw_version': 'rpi2mqtt',
        #                  'model': self.device_model,
        #                  'manufacturer': 'Generic'}

        # config = json.dumps({'name': self.name + '_' + self.device_model,
        #                      'device_class': self.device_class,
        #                      'value_template': "{{ value_json.state }}",
        #                      'unique_id': self.name + '_' + self.device_model + '_rpi2mqtt',
        #                      'state_topic': self.topic,
        #                      "json_attributes_topic": self.topic + '/state',
        #                     #  "command_topic": self.topic + '/set',
        #                      'device': device_config})

        # mqtt.publish('homeassistant/{}/{}_{}/config'.format(self.device_class, self.name, self.device_model), config)
        # logging.debug("Published MQTT discovery config to homeassistant/{}/{}_{}/config.format(self.device_class, self.name, self.device_model)")
        GPIO.setmode(GPIO.BCM)
        # g.setup(self.pin, g.OUT)
        # mqtt.subscribe(self.topic + '/set', self.mqtt_callback)

        if self.normally_open:
            mode = GPIO.PUD_UP
        else:
            mode = GPIO.PUD_DOWN

        GPIO.setup(self.pin, GPIO.IN, pull_up_down=mode)
        logging.debug('Reed Switch {} configured as input on GPIO{} witn pull_up_down set to {}'.format(self.name, self.pin, mode))

    def state(self):
        state = GPIO.input(self.pin) 
        logging.debug("Reed Switch {}: GPIO{} state is {}".format(self.name, self.pin, state))
        if state == 1:
            return "ON"
        else:
            return "OFF"

    def payload(self):
        return json.dumps({'state': self.state()})

    def callback(self, *args):
        mqtt.publish(self.topic, self.payload())


class BinarySensor(Sensor):

    def __init__(self, name, pin, topic ):
        super(BinarySensor, self).__init__(name, pin, topic, None, 'binary')
        self.setup()

    def setup(self):
        pass

    def state(self):
        pass
