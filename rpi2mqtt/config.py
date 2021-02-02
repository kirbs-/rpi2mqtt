import logging
import sys
import yaml
from dotmap import DotMap
import pathlib
logging.basicConfig(stream=sys.stdout, format='%(asctime)s:%(levelname)s:%(message)s')


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
                cls._config = DotMap(yaml.safe_load(f))
                config_filename = pathlib.Path(f.name).absolute()
                logging.info("Loaded config file {}".format(config_filename))
            Config.set_log_level(cls._config.loglevel)
        return cls._config

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


def generate_config(config_filename):
    with open(config_filename, 'w') as f: 
        default_config = {
            "logging": 'warn',
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

