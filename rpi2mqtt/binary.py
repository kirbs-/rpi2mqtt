import RPi.GPIO as GPIO
import rpi2mqtt.mqtt as mqtt
import json
import logging

logging.basicConfig(level=logging.INFO)


class Sensor(object):

    def __init__(self, pin, topic):
        self.pin = pin
        self.topic = topic


class ReedSwitch(Sensor):
    """
    Extends simple binary sensor by adding configuration for normally open or normally closed reed switches.
    """

    def __init__(self, pin, topic, name, normally_open):
        super(ReedSwitch, self).__init__(pin, topic)
        self.normally_open = normally_open
        self.name = name
        self.setup()

    def setup(self):
        """
        Setup GPIO pin to read input value.
        :return: None
        """
        device_config = {'name': "Reed Switch",
                         'identifiers': self.name,
                         'sw_version': 'rpi2mqtt',
                         'model': "Reed Switch",
                         'manufacturer': 'Generic'}

        config = json.dumps({'name': self.name + '_reed_switch',
                             # 'device_class': 'switch',
                             'value_template': "{{ value_json.state }}",
                             'unique_id': self.name + '_reed_switch_rpi2mqtt',
                             'state_topic': self.topic,
                             "json_attributes_topic": self.topic + '/state',
                            #  "command_topic": self.topic + '/set',
                             'device': device_config})

        mqtt.publish('homeassistant/sensor/{}_{}/config'.format(self.name, 'reed_switch'), config)
        logging.info("Published MQTT discovery config to homeassistant/sensor/{}_{}/config".format(self.name, 'reed_switch'))
        GPIO.setmode(GPIO.BCM)
        # g.setup(self.pin, g.OUT)
        # mqtt.subscribe(self.topic + '/set', self.mqtt_callback)

        if self.normally_open:
            mode = GPIO.PUD_UP
        else:
            mode = GPIO.PUD_DOWN

        GPIO.setup(self.pin, GPIO.IN, pull_up_down=mode)

    def state(self):
        if GPIO.input(self.pin) == 1:
            return "OFF"
        else:
            return "ON"

    def payload(self):
        return json.dumps({'state': self.state()})
        # return self.state()

    def callback(self, *args):
        mqtt.publish(self.topic, self.payload())
