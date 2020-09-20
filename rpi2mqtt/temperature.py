# coding=utf-8
import Adafruit_DHT as dht
import json
import rpi2mqtt.mqtt as mqtt
from rpi2mqtt.base import Sensor, SensorGroup
import logging

import smbus2
import bme280


class DHT(object):

    def __init__(self, pin, topic, name, device_class, dht_type):
        self.type = dht_type
        self.pin = pin
        self.topic = topic
        self.name = name
        self.device_class = device_class
        self.setup()

    def read(self, scale='F'):
        self.humidity, self.temperature = dht.read_retry(22, self.pin)
        #print humidity
        #print temperature

        if scale == 'F':
            return json.dumps({'humidity': self._humidity, 'temperature': self.temperature_F})
        else:
            return json.dumps({'humidity': self._humidity, 'temperature': self.temperature})

    @property
    def temperature_F(self):
        try:
            return round(self.temperature_C * 1.8 + 32.0, 1)
        except:
            return None

    @property
    def temperature_C(self):
        return round(self.temperature, 1)

    @property
    def _humidity(self):
        return round(self.humidity, 3)

    def setup(self):
        # config = json.dumps({'name': self.name, 'device_class': self.device_class})

        device_config = {'name': "Laundry Room Climate",
                         'identifiers': self.name,
                         'sw_version': 'rpi2mqtt',
                         'model': "DHT 22",
                         'manufacturer': 'Generic'}

        config = json.dumps({'name': self.name + '_temperature',
                             'device_class': 'temperature',
                             'unit_of_measurement': '°F',
                             'value_template': "{{ value_json.temperature }}",
                             'unique_id': self.name + '_temperature_rpi2mqtt',
                             'state_topic': self.topic,
                             "json_attributes_topic": self.topic,
                             'device': device_config})

        mqtt.publish('homeassistant/sensor/{}_{}/config'.format(self.name, 'temp'), config)

        config = json.dumps({'name': self.name + '_humidity',
                             'device_class': 'humidity',
                             'json_attributes_topic': self.topic,
                             'unit_of_measurement': '%',
                             'value_template': "{{ value_json.humidity }}",
                             'unique_id': self.name + '_humidity_rpi2mqtt',
                             'state_topic': self.topic,
                             'device': device_config})

        mqtt.publish('homeassistant/sensor/{}_{}/config'.format(self.name, 'humidity'), config)

    def state(self):
        return self.read()

    def payload(self):
        # return json.dumps({'state': self.state()})
        # return json.dumps(self.state())
        return self.state()

    def callback(self):
        mqtt.publish(self.topic, self.payload())


class GenericTemperature(Sensor):
    @property
    def homeassistant_mqtt_config(self):
        config = super(GenericTemperature, self).homeassistant_mqtt_config
        config['value_template'] = "{{ value_json.temperature }}"
        return config


class GenericHumidity(Sensor):
    @property
    def homeassistant_mqtt_config(self):
        config = super(GenericHumidity, self).homeassistant_mqtt_config
        config['value_template'] = "{{ value_json.humidity }}"
        return config


class GenericPressure(Sensor):
    @property
    def homeassistant_mqtt_config(self):
        config = super(GenericPressure, self).homeassistant_mqtt_config
        config['value_template'] = "{{ value_json.pressure }}"
        return config


class BME280(SensorGroup):

    def __init__(self, name, topic, **kwargs):

        self.port = 1
        self.address = 0x76
        self.bus = smbus2.SMBus(port)
        self.calibration_params = bme280.load_calibration_params(bus, address)
        self.device_type = 'BME280'

        # the sample method will take a single reading and return a
        # compensated_reading object
        # data = bme280.sample(bus, address, calibration_params)

        # TODO sensors with multiple reading types can be supported with publishing one message
        # but each reading type must be setup seperately with different names and value_json attributes.

    
    def setup_temperature(self):
        sensor = GenericTemperature(self.name, None, self.topic, 'temperature', self.device_type)
        self.sensors.append(sensor)

    def setup_humidity(self):
        sensor = GenericHumidity(self.name, None, self.topic, 'humidity', self.device_type)
        self.sensors.append(sensor)

    def setupPressure(self):
        sensor = GenericPressure(self.name, None, self.topic, 'pressure', self.device_type)
        self.sensors.append(sensor)

    def state(self):
        return bme280.sample(bus, address, calibration_params)

    # def payload(self)