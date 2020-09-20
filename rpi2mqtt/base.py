import rpi2mqtt.mqtt as mqtt
import json
import logging
from rpi2mqtt.version import __version__

logging.basicConfig(level=logging.INFO)


class Sensor(object):

    def __init__(self, name, pin, topic, device_class, device_model):
        self.name = name
        self.pin = pin
        self.topic = topic
        self.device_class = device_class
        self.device_model = device_model
        self.publish_mqtt_discovery()

    @property
    def device_config(self):
        return {'name': self.name,
                         'identifiers': self.name,
                         'sw_version': 'rpi2mqtt {}'.format(__version__),
                         'model': self.device_model,
                         'manufacturer': 'Generic'}

    @property
    def homeassistant_mqtt_config(self):
        return json.dumps({'name': self.name + '_' + self.device_model,
                             'device_class': self.device_class,
                             'value_template': "{{ value_json.state }}",
                             'unique_id': self.name + '_' + self.device_model + '_rpi2mqtt',
                             'state_topic': self.topic,
                             "json_attributes_topic": self.topic + '/state',
                             'device': self.device_config})

    def publish_mqtt_discovery(self):

        mqtt.publish('homeassistant/{}/{}_{}/config'.format(self.device_class, self.name, self.device_model), self.homeassistant_mqtt_config)
        logging.debug("Published MQTT discovery config to homeassistant/{}/{}_{}/config".format(
            self.device_class, self.name, self.device_model))

    def setup(self):
        raise NotImplementedError("Setup method is required.")

    def state(self):
        raise NotImplementedError("State method is required.")

    def payload(self):
        return json.dumps({'state': self.state()})

    def callback(self, *args):
        mqtt.publish(self.topic, self.payload())