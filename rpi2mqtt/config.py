import logging
import sys
import yaml
# from dotmap import DotMap
import pathlib
from dataclasses import dataclass, asdict
# from typing import Optional
from collections.abc import Mapping


logging.basicConfig(stream=sys.stdout, format='%(asctime)s:%(levelname)s:%(message)s')


@dataclass
class SensorConfig(Mapping):
    type: str
    name: str
    topic: str
    pin: int = None
    # device_class: str = None
    # binary sensor options
    normally_open: bool = None
    # hestia pi thermostat options
    mode: str = None
    heat_setpoint: float = None
    cool_setpoint: float = None
    aux_enabled: str = None
    set_point_tolerance: float = None
    min_run_time: int = None
    min_trigger_cooldown_time: int = None
    temperature_history_period: int = None
    minimum_temp_rate_of_change: int = None
    dry_run: bool = None
    # ibeacon options
    beacon_uuid: str = None
    beacon_away_timeout: int = None

    # override required Mapping functions
    def __iter__(self):
        for k, v in self.__dict__.items():
            yield k

    def __len__(self):
        return len(asdict(self))

    def __getitem__(self, item):
        return asdict(self).get(item)


@dataclass
class MqttConfig:
    host: str
    port: int
    username: str = None
    password: str = None
    ca_cert: str = None
    retries: int = 3


@dataclass
class Conf:
    # filename: str
    mqtt: MqttConfig
    polling_interval: int
    log_level: str
    sensors: list

    def to_dict(self):
        return asdict(self)


class Config():
    """Config holder singleton. Use Config.get_instance() in submodules to access. Initial call must include 'filename'.

    Attributes:
        [type]: [description]
    """
    _config = None
    _filename = None

    @classmethod
    def get_instance(cls, filename=None):
        if filename:
            cls._filename = filename

        if not cls._config and cls._filename:
            with open(cls._filename, 'r') as f:
                # cls._config = DotMap(yaml.safe_load(f))
                Config.load(yaml.safe_load(f))
                config_filename = pathlib.Path(f.name).absolute()
                logging.info("Loaded config file {}".format(config_filename))
            Config.set_log_level(cls._config.log_level)
        return cls._config

    @classmethod
    def load(cls, config):
        cls._config = Conf(**config)
        cls._config.mqtt = MqttConfig(**cls._config.mqtt)
        cls._config.sensors = [SensorConfig(**sensor) for sensor in cls._config.sensors]

    @classmethod
    def to_dict(cls):
        _cfg = asdict(cls._config)
        sensors = []
        for sensor in _cfg['sensors']:
            sensors.append({k:v for k,v in sensor.items() if v})
        _cfg['sensors'] = sensors
        return _cfg

    @staticmethod
    def set_log_level(level):
        _level = logging.WARN
        if level == 'info':
            _level = logging.INFO
        elif level == 'debug':
            _level = logging.DEBUG
        elif level == 'error':
            _level = logging.ERROR
        logger = logging.getLogger().setLevel(_level)

    @classmethod
    def save(cls):
        logging.info("Saving config file...")
        with open(cls._filename, 'w') as f:
            yaml.dump(cls._config.to_dict(), f)


def generate_config(config_filename):
    with open(config_filename, 'w') as f: 
        default_config = {
            "log_level": 'warn',
            'polling_interval': 300,
            'mqtt': {
                'host': 'hostname',
                'port': 1883,
                'username': 'mqtt_user',
                'password': 'mqtt_password',
                'retries': 3,
                'ca_cert': '/path/to/certificate'
            },
            'sensors': [
                {'name': 'sensor_name', 'type': 'sensor_type', 'pin': 'gpio pin number'}
            ]}
        f.write(yaml.dump(default_config))

