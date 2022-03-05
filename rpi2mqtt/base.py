from rpi2mqtt.mqtt import MQTT as mqtt
import json
import logging
from rpi2mqtt.version import __version__
import RPi.GPIO as GPIO

# logging.basicConfig(level=logging.INFO)


SENSORS = {}
def sensor(func):
    def wrap(*args):
        if args.name not in SENSORS:
            SENSORS[args.name] = [func]
        else:
            SENSORS[args.name].append(func)
    return wrap

GPIO.setmode(GPIO.BCM)

class Sensor(object):

    BINARY_SENSORS = ['reed', 'binary_sensor']

    def __init__(self, name, pin, topic, device_class, device_model, **kwargs):
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
        return {'name': '{}_{}'.format(self.name, self.device_class),
                'device_class': self.device_class,
                'value_template': "{{ value_json.state }}",
                'unique_id': '{}_{}_{}_rpi2mqtt'.format(self.name, self.device_model, self.device_class),
                'state_topic': self.topic,
                "json_attributes_topic": self.topic,
                'device': self.device_config}

    @property
    def homeassistant_mqtt_config_json(self):
        return json.dumps(self.homeassistant_mqtt_config)

    @property
    def homeassistant_mqtt_config_topic(self):
        homeassistant_sensor_type = 'sensor'
        if self.device_class in Sensor.BINARY_SENSORS:
            homeassistant_sensor_type = 'binary_sensor'
        elif self.device_class in ['switch', 'off', 'heat', 'cool', 'aux']:
            homeassistant_sensor_type = 'switch'
        elif self.device_class == 'climate':
            homeassistant_sensor_type = 'climate'

        return 'homeassistant/{}/{}_{}/config'.format(homeassistant_sensor_type, self.name, self.device_class)

    def publish_mqtt_discovery(self):

        mqtt.publish(self.homeassistant_mqtt_config_topic, self.homeassistant_mqtt_config_json)
        logging.debug("Published MQTT discovery config to {}".format(self.homeassistant_mqtt_config_topic))

    def setup(self):
        raise NotImplementedError("Setup method is required.")

    def state(self):
        raise NotImplementedError("State method is required.")

    def payload(self):
        return json.dumps({'state': self.state()})

    def callback(self, **kwargs):
        mqtt.publish(self.topic, self.payload())


class SensorGroup(Sensor):
    """Group of multiple sensors e.g. DHT22 or BME280.

    Sensors with multiple capabilities (i.e. temperature, humididty, pressure, presenece, etc.) must be setup as
    individual sesnsors in home assistant. Updating the state however, is done with a single message to the sensor's
    state topic.

    Attributes:
        name (str): Sensor name
        pin (int): Sensor GPIO pin (BCM pin nanme)
        topic (str): Base topic name. This is prepended to '/state' and '/config' to create respective topics in HA.
        device_class (str): Home Assistant device class for this sensor.
        device_type (str): Type of sensor. e.g. DHT22, Reed Switch, etc. 
    """
    def __init__(self, name, pin, topic, device_class, device_type):
        self.name = name
        self.pin = pin
        self.topic = topic
        self.device_class = device_class
        self.device_type = device_type
        self.sensors = []

    def setup(self):
        for sensor in self.sensors:
            sensor.setup()

    # def state(self):
    #     raise NotImplementedError('State method is required.')

    # def payload(self): 
    #     raise NotImplementedError('Payload method is required.')

    # def callback(self):
    #     raise NotImplementedError('Callback method is required.')


