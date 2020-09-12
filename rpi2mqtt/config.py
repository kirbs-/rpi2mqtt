import yaml
from dotmap import DotMap
import os
import logging
import pathlib


with open(os.path.join(os.path.dirname(__file__), 'config.yaml'), 'r') as f:
    config = DotMap(yaml.safe_load(f))
    config_filename = pathlib.Path(f.name).absolute()
    logging.info("Loaded config file {}".format(config_filename))
