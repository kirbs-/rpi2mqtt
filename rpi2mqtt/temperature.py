# coding=utf-8
import Adafruit_DHT as dht
import json
from rpi2mqtt.mqtt import MQTT as mqtt
from rpi2mqtt.base import Sensor, SensorGroup, sensor
import logging
import os
import glob
import smbus2
import bme280
import re


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
            pass

    @property
    def temperature_C(self):
        try:
            return round(self.temperature, 1)
        except:
            pass

    @property
    def _humidity(self):
        try:
            return round(self.humidity, 3)
        except:
            pass

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

    def callback(self, **kwargs):
        mqtt.publish(self.topic, self.payload())


class GenericTemperature(Sensor):
    @property
    def homeassistant_mqtt_config(self):
        config = super(GenericTemperature, self).homeassistant_mqtt_config
        config['value_template'] = "{{ value_json.temperature }}"
        config['unit_of_measurement'] = '°F'
        return config

    def setup(self):
        pass

    def state(self):
        pass

class GenericHumidity(Sensor):
    @property
    def homeassistant_mqtt_config(self):
        config = super(GenericHumidity, self).homeassistant_mqtt_config
        config['value_template'] = "{{ value_json.humidity }}"
        config['unit_of_measurement'] = '%'
        return config

    def setup(self):
        pass

    def state(self):
        pass

class GenericPressure(Sensor):
    @property
    def homeassistant_mqtt_config(self):
        config = super(GenericPressure, self).homeassistant_mqtt_config
        config['value_template'] = "{{ value_json.pressure }}"
        return config

    def setup(self):
        pass

    def state(self):
        pass

class BME280(SensorGroup):

    def __init__(self, name, topic, **kwargs):
        super(BME280, self).__init__(name, None, topic, 'temperature/humidity/pressure', 'BME280', **kwargs)
        self.port = 1
        self.address = 0x76
        self.bus = smbus2.SMBus(self.port)
        self.calibration_params = bme280.load_calibration_params(self.bus, self.address)
        self.topic = topic
        self.device_type = 'BME280'
        self.setup_temperature()
        self.setup_humidity()
        self.setup_pressure()


        # the sample method will take a single reading and return a
        # compensated_reading object
        # data = bme280.sample(bus, address, calibration_params)

        # TODO sensors with multiple reading types can be supported with publishing one message
        # but each reading type must be setup seperately with different names and value_json attributes.
    
    # @sensor
    def setup_temperature(self):
        sensor = GenericTemperature(self.name, None, self.topic, 'temperature', self.device_type)
        self.sensors.append(sensor)
    
    # @sensor
    def setup_humidity(self):
        sensor = GenericHumidity(self.name, None, self.topic, 'humidity', self.device_type)
        self.sensors.append(sensor)

    # @sensor
    def setup_pressure(self):
        sensor = GenericPressure(self.name, None, self.topic, 'pressure', self.device_type)
        self.sensors.append(sensor)

    def state(self):
        data = bme280.sample(self.bus, self.address, self.calibration_params)
        return {'id': str(data.id),
            'timestamp': str(data.timestamp),
            'temperature': data.temperature * 1.8 + 32,
            'pressure': data.pressure,
            'humidity': data.humidity,
            }

    def payload(self):
        return json.dumps(self.state())


class OneWire(Sensor):
    """Must enable one wire interface on Raspberry Pi and load modprobe w1-gpio and w1-therm drivers."""
    BASE_DIR = '/sys/bus/w1/devices/'
    # These tow lines mount the device:
    try:
        os.system('modprobe w1-gpio')
        os.system('modprobe w1-therm')
    except:
        logging.warn('Unable to load w1-gpio and w1-therm.')

    TEMP_REGEX = re.compile('.*? t=(\d*)')

    def __init__(self, name, topic, **kwargs):
        self.devices = {}
        self.temperature = None
        self.setup()
        super(OneWire, self).__init__(name, None, topic, 'temperature', 'One wire', **kwargs)

    def setup(self):
        for device in glob.glob( OneWire.BASE_DIR + '**/w1_slave'):
            w1_id = device.split('/')[-2]
            self.devices[w1_id] = device
        return True

    def state(self):
        for device, filename in self.devices.items():
            with open(filename, 'r') as f:
                self.temperature = OneWire.parse_one_wire_file(device, f.read())

            return self.temperature_F

    def payload(self):
        return json.dumps({
            'temperature': self.state(),
            'state': self.state()
        })
    
    @property
    def temperature_F(self):
        try:
            return round(self.temperature * 1.8 + 32.0, 1)
        except:
            pass

    @property
    def temperature_C(self):
        try:
            return round(self.temperature, 1)
        except:
            pass

    @staticmethod
    def parse_one_wire_file(device, text):
        match = OneWire.TEMP_REGEX.search(text)
        if text:
            return float(match.groups()[0]) / 1000.0
        else:
            logging.warn('Unable to parse temperature for one wire device {}.'.format(device))
