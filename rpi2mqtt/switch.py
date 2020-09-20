from rpi2mqtt.base import Sensor
import rpi2mqtt.mqtt as mqtt
import json
from datetime import datetime, timedelta
import RPi.GPIO as g
import logging

logging.basicConfig(level=logging.INFO)

class Switch(Sensor):

    def __init__(self, name, pin, topic):
        super(Switch, self).__init__(name, pin, topic, 'switch', 'generic_switch')
        self.power_state = 'OFF'
        self.last_seen = datetime.now()
        self.setup()


    @property
    def homeassistant_mqtt_config(self):
        config = super(Switch, self).homeassistant_mqtt_config
        config['value_template'] = "{{ value_json.power_state }}"
        config['command_topic'] = self.topic + '/set'
        return config

    def setup(self):
        """
        Setup Home Assistant MQTT discover for ibeacons.
        :return: None
        """
        # device_config = {'name': "Switch",
        #                  'identifiers': self.name,
        #                  'sw_version': 'rpi2mqtt',
        #                  'model': "Switch",
        #                  'manufacturer': 'Generic'}

        # config = json.dumps({'name': self.name + '_switch',
        #                      # 'device_class': 'switch',
        #                      'value_template': "{{ value_json.power_state }}",
        #                      'unique_id': self.name + '_switch_rpi2mqtt',
        #                      'state_topic': self.topic,
        #                      "json_attributes_topic": self.topic + '/state',
        #                      "command_topic": self.topic + '/set',
        #                      'device': device_config})

        # mqtt.publish('homeassistant/switch/{}_{}/config'.format(self.name, 'switch'), config)

        # setup GPIO
        g.setmode(g.BCM)
        g.setup(self.pin, g.OUT)
        mqtt.subscribe(self.homeassistant_mqtt_config['command_topic'], self.mqtt_callback)

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
        # read output pin state
        pin_state = g.input(self.pin)

        # convert to home assistant on/off state defaults
        # https://www.home-assistant.io/integrations/switch.mqtt/#state_on
        if pin_state == 1:
            self.power_state = 'ON'
        elif pin_state == 0:
            self.power_state = 'OFF'
        else:
            self.power_state = 'INVALID'

        return self.power_state

    def payload(self):
        return json.dumps({'power_state': self.state()})

    # def callback(self, *args):
    #     mqtt.publish(self.topic, self.payload())

    def mqtt_callback(self, client, userdata, message):
        try:
            # print(message)
            logging.info("Received command message: {}".format(message))
            payload = message.payload
            if payload == 'ON':
                self.on()
            elif payload == 'OFF':
                self.off()
        except Exception as e:
            logging.error('Unable to proces message.', e)

        mqtt.publish(self.topic, self.payload())