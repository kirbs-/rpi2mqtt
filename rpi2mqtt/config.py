import logging
import sys
logging.basicConfig(level=logging.INFO, stream=sys.stdout)

import yaml
from dotmap import DotMap
import os
import pathlib
import pkg_resources


# logging.getLogger().setLevel(logging.DEBUG)
config = None
config_file =  pkg_resources.resource_filename(__name__,'config.yaml')
# template = pkg_resources.resource_string(resource_package, resource_path)
# or for a file-like stream:
# template = pkg_resources.resource_stream(__name__, config_file)
# config_filename = None

def load():
    global config
    with open(config_file, 'r') as f:
        config = DotMap(yaml.safe_load(f))
        config_filename = pathlib.Path(f.name).absolute()
        logging.info("Loaded config file {}".format(config_filename))
    return config


def save(filename):
    with open(filename, 'r') as f:
        with open(config_file, 'w') as w:
            w.write(f.read())
    return load()

load()