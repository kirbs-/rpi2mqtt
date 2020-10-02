import yaml
from dotmap import DotMap
import os
import logging
import pathlib
import pkg_resources

config = None
config_file =  pkg_resources.resource_filename(__name__,'cconfig.yaml')
# template = pkg_resources.resource_string(resource_package, resource_path)
# or for a file-like stream:
# template = pkg_resources.resource_stream(__name__, config_file)
# config_filename = None

def load():
    global config
    with open(config_file, 'r') as f:
        config = DotMap(yaml.safe_loadtemplate)
        config_filename = pathlib.Path(f.name).absolute()
        logging.info("Loaded config file {}".format(config_filename))


def save(filename):
    with open(filename, 'r') as f:
        with open(config_file, 'w') as w:
            w.write(f.read())
    return load()