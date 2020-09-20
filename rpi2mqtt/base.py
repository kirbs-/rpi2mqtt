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
        return {'name': '{}_{}'.format(self.name, self.device_model),
                'device_class': self.device_class,
                'value_template': "{{ value_json.state }}",
                'unique_id': '{}_{}_rpi2mqtt'.format(self.name, self.device_model),
                'state_topic': self.topic,
                "json_attributes_topic": '{}/state'.format(self.topic),
                'device': self.device_config}

    @property
    def homeassistant_mqtt_config_json(self):
        return json.dumps(self.homeassistant_mqtt_config)

    @property
    def homeassistant_mqtt_config_topic(self):
        return 'homeassistant/{}/{}_{}/config'.format(self.device_class, self.name, self.device_model)

    def publish_mqtt_discovery(self):

        mqtt.publish(self.homeassistant_mqtt_config_topic, self.homeassistant_mqtt_config_json)
        logging.debug("Published MQTT discovery config to {}".format(self.homeassistant_mqtt_config_topic))

    def setup(self):
        raise NotImplementedError("Setup method is required.")

    def state(self):
        raise NotImplementedError("State method is required.")

    def payload(self):
        return json.dumps({'state': self.state()})

    def callback(self, *args):
        mqtt.publish(self.topic, self.payload())