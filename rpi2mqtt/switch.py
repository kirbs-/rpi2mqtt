from rpi2mqtt.base import Sensor
from rpi2mqtt.mqtt import MQTT as mqtt
import json
from datetime import datetime, timedelta
import RPi.GPIO as g
import logging


class BasicSwitch(Sensor):
    """Basic switch setup to control GPIO pins and read their state

    Args:
        Sensor ([type]): [description]
    """
    def __init__(self, name, pin, topic, device_class='switch', device_type='generic_switch'):
        super(BasicSwitch, self).__init__(name, pin, topic, device_class, device_type)
        self.power_state = 'OFF'
        self.last_seen = datetime.now()
        # self.setup()
        # g.setmode(g.BCM)

    def setup(self, lazy_setup=True):
        """
        Setup Home Assistant MQTT discover for ibeacons.
        :return: None
        """
        # setup GPIO
        g.setmode(g.BCM)
        if not type(self.pin) == list:
            self.pin = [self.pin]

        for pin in self.pin:
            g.setup(pin, g.IN)
        
        if not lazy_setup:
            self.setup_output()

    def setup_output(self):
        logging.info("Setting pins {} to ouptut.".format(self.pin))
        g.setup(self.pin, g.OUT, initial=g.LOW)

    def on(self):
        try:
            g.output(self.pin, g.HIGH)
        except RuntimeError as e:
            logging.info("Switch output not configured yet. Setting up pins {}".format(self.pin))
            self.setup_output()
            g.output(self.pin, g.HIGH)
        self.power_state = 'ON'

    def off(self):
        try:
            g.output(self.pin, g.LOW)
        except RuntimeError as e:
            logging.info("Switch output not configured yet. Setting up pins {}".format(self.pin))
            self.setup_output()
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

    def publish_mqtt_discovery(self):
        pass




class Switch(Sensor):

    def __init__(self, name, pin, topic, device_class='switch', device_type='generic_switch'):
        super(Switch, self).__init__(name, pin, topic, device_class, device_type)
        self.power_state = 'OFF'
        self.last_seen = datetime.now()
        self.setup()


    @property
    def homeassistant_mqtt_config(self):
        config = super(Switch, self).homeassistant_mqtt_config
        config['value_template'] = "{{ value_json.power_state }}"
        config['command_topic'] = self.topic + '/set'
        del config['device_class']
        return config

    def setup(self, lazy_setup=True):
        """
        Setup Home Assistant MQTT discover for ibeacons.
        :return: None
        """
        # setup GPIO
        g.setmode(g.BCM)
        if not type(self.pin) == list:
            self.pin = [self.pin]

        for pin in self.pin:
            g.setup(pin, g.IN)

        # for pin in self.pin:
        if not lazy_setup:
            self.setup_output()
        mqtt.subscribe(self.homeassistant_mqtt_config['command_topic'], self.mqtt_callback)

    def setup_output(self):
        logging.debug("Setting pins {} to ouptut.".format(self.pin))
        g.setup(self.pin, g.OUT, initial=g.LOW)

    def on(self):
        try:
            g.output(self.pin, g.HIGH)
        except RuntimeError as e:
            logging.info("Switch output not configured yet. Setting up pins {}".format(self.pin))
            self.setup_output()
            g.output(self.pin, g.HIGH)
        self.power_state = 'ON'

    def off(self):
        try:
            g.output(self.pin, g.LOW)
        except RuntimeError as e:
            logging.info("Switch output not configured yet. Setting up pins {}".format(self.pin))
            self.setup_output()
            g.output(self.pin, g.LOW)
        self.power_state = 'OFF'

    def toggle(self):
        if self.power_state == 'ON':  # and self.last_seen + timedelta(seconds=self.away_timeout) < datetime.now():
            self.off()
        else:
            self.on()

    def state(self):
        # read output pin state
        # TODO refactor switch into single pin & multi pin classes
        pin_state = 0
        for _pin in self.pin:
            pin_state += g.input(_pin)

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
    @mqtt.pongable
    def mqtt_callback(self, client, userdata, message):
        try:
            # print(message)
            # logging.info("Received command message: {}".format(payload))
            payload = message.payload.decode()
            logging.info("Received command message: {} on topic ".format(payload, message.topic))
            if payload == 'ON':
                self.on()
            elif payload == 'OFF':
                self.off()
        except Exception as e:
            logging.error('Unable to proces message.', e)

        mqtt.publish(self.topic, self.payload())

    