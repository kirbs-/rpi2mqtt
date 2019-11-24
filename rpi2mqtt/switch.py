from rpi2mqtt.binary import Sensor
import rpi2mqtt.mqtt as mqtt
import json
from datetime import datetime, timedelta
import RPi.GPIO as g


class Switch(Sensor):

    def __init__(self, pin, name, topic):
        super(Switch, self).__init__(None, topic)
        self.name = name
        self.power_state = 'OFF'
        self.last_seen = datetime.now()
        self.setup()

    def setup(self):
        """
        Setup Home Assistant MQTT discover for ibeacons.
        :return: None
        """
        device_config = {'name': "Switch",
                         'identifiers': self.name,
                         'sw_version': 'rpi2mqtt',
                         'model': "Switch",
                         'manufacturer': 'Generic'}

        config = json.dumps({'name': self.name + '_switch',
                             'device_class': 'switch',
                             'value_template': "{{ value_json.power_state }}",
                             'unique_id': self.name + '_switch_rpi2mqtt',
                             'state_topic': self.topic,
                             "json_attributes_topic": self.topic + '/state',
                             "command_topic": self.topic + '/set',
                             'device': device_config})

        mqtt.publish('homeassistant/switch/{}_{}/config'.format(self.name, 'switch'), config)

        # setup GPIO
        g.setmode(g.BCM)
        g.setup(self.pin, g.OUT)

    def on(self):
        g.output(self.pin, g.HIGH)
        self.power_state = 'ON'

    def off(self):
        g.output(self.pin, g.LOW)
        self.power_state = 'OFF'

    def toggle(self):
        if self.power_state == 'ON':  # and self.last_seen + timedelta(seconds=self.away_timeout) < datetime.now():
            self.off()
        else:
            self.on()

    def state(self):
        return json.dumps({'power_state': self.power_state})

    def payload(self):
        return self.state()

    def callback(self, client, userdata, message):
        payload = json.loads(message.payload)
        if payload.state == 'ON':
            self.on()
        elif payload.state == 'OFF':
            self.off()

        mqtt.publish(self.topic, self.payload())