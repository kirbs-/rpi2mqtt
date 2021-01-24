import logging
import sys
# logging.basicConfig(level=logging.INFO, stream=sys.stdout)

import yaml
from dotmap import DotMap
import os
import pathlib
import pkg_resources


# logging.getLogger().setLevel(logging.DEBUG)
config = None
CONFIG_FILE =  pkg_resources.resource_filename(__name__,'config.yaml')
# template = pkg_resources.resource_string(resource_package, resource_path)
# or for a file-like stream:
# template = pkg_resources.resource_stream(__name__, config_file)
# config_filename = None

def load():
    global config
    with open(CONFIG_FILE, 'r') as f:
        config = DotMap(yaml.safe_load(f))
        config_filename = pathlib.Path(f.name).absolute()
        logging.info("Loaded config file {}".format(config_filename))
    set_log_level()
    return config


def save(filename):
    with open(filename, 'r') as f:
        with open(CONFIG_FILE, 'w') as w:
            w.write(f.read())
    return load()


def set_log_level():
    global config
    level = logging.WARN
    if config.loglevel == 'info':
        level = logging.INFO
    elif config.loglevel == 'debug':
        level = logging.DEBUG
    elif config.loglevel == 'error':
        level = logging.ERROR
    logging.basicConfig(level=level, stream=sys.stdout)

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

try:
    load()
except FileNotFoundError as e:
    logging.error("No confiuration file specified. Run `rpi2mqtt --init` to generate configuration template.")