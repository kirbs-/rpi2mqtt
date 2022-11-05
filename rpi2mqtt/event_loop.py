# import asyncio
import logging
import traceback
import argparse
import subprocess
import sys
import schedule

from rpi2mqtt.config import Config
from rpi2mqtt.binary import *
from rpi2mqtt.temperature import *
from rpi2mqtt.ibeacon import Scanner
from rpi2mqtt.switch import Switch
from rpi2mqtt.thermostat import HestiaPi
import time

try:
    from beacontools import BeaconScanner, IBeaconFilter
except:
    print("Unable to load beacontools")


# setup CLI parser
parser = argparse.ArgumentParser()
parser.add_argument("-c", "--config",
                help="Path to config.yaml")

parser.add_argument('-d', '--dry-run', 
                help='Test drive config without triggering callbacks.')

parser.add_argument('--generate-config',
                help="Generate config.yaml template.",
                action='store_true')

parser.add_argument('--install-service',
                help='Install rpi2mqtt as systemd service.',
                action='store_true')

parser.add_argument('--install-user-service',
                help='Install rpi2mqtt as user systemd service.',
                action='store_true')


def main():
    config = None
    args = parser.parse_args() 

    if args.generate_config:
        Config.generate_config('config.yaml')
        sys.exit(0)

    if args.install_service:
        username = input("User to run service as [pi]: ") or 'pi'
        config_path = input("Enter full path to config.yaml: ")
        # _path = input("Path rpi2mqtt executable (run `which rpi2mqtt`): ")
        _path = subprocess.check_output(['which', 'rpi2mqtt']).decode().strip()
        install_service(username, _path, config_path, 'system')
        sys.exit(0)

    if args.install_user_service:
        username = input("User to run service as [pi]: ") or 'pi'
        config_path = input("Enter full path to config.yaml: ")
        # _path = input("Path rpi2mqtt executable (run `which rpi2mqtt`): ")
        _path = subprocess.check_output(['which', 'rpi2mqtt']).decode().strip()
        install_service(username, _path, config_path, 'user')
        sys.exit(0)

    scanner = None

    if args.config:
        config = Config.get_instance(filename=args.config)

    if not config:
        logging.error("No configuration file present.")
        sys.exit(1)

    # start MQTT client
    from rpi2mqtt.mqtt import MQTT
    MQTT.setup()

    sensor_list = []
    if len(config.sensors) > 0:
        for _, sensor in config.sensors.items():
            s = None
            if sensor.type == 'dht22':
                s = DHT(sensor.pin, sensor.topic, sensor.name, 'sensor', sensor.type)
            elif sensor.type == 'ibeacon':
                s = Scanner(sensor.name, sensor.topic, sensor.beacon_uuid, sensor.beacon_away_timeout)
            elif sensor.type == 'switch':
                s = Switch(sensor.name, sensor.pin, sensor.topic)
            elif sensor.type == 'reed':
                s = ReedSwitch(sensor.name, sensor.pin, sensor.topic, sensor.normally_open, sensor.get('device_type'))
            elif sensor.type == 'bme280':
                s = BME280(sensor.name, sensor.topic)
            elif sensor.type == 'hestiapi':
                s = HestiaPi(**sensor)
            elif sensor.type == 'onewire':
                s = OneWire(sensor.name, sensor.topic)
            else:
                logging.warn('Sensor {} found in config, but was not setup.'.format(sensor.name))
            if s:
                sensor_list.append(s)

        try:
            scanner = BeaconScanner(sensor_list[1].process_ble_update) # TODO update to search sensor list and setup scanner accordingly.
            scanner.start()
        except:
            logging.error("Beacon scanner did not start")
    else:
        logging.warn("No sensors defined in {}".format(args.config))

    schedule.every().day.at("01:00").do(MQTT.refresh_subscriptions)

    try:
        while True:

            for sensor in sensor_list:
                sensor.callback()

            time.sleep(config.polling_interval)
            MQTT.ping_subscriptions()
            schedule.run_pending()

    except:
        traceback.print_exc()
        MQTT.client.loop_stop()

        if scanner:
            scanner.stop()


def install_service(username, _path, config_path, _type):
    template = """[Unit]
Description=rpi2mqtt Service
After=network-online.target

[Service]
# replace user with an existing system user
Restart=on-failure
User={username}
ExecStart={_path} -c {config_path}

[Install]
WantedBy=multi-user.target
    """.format(username=username, _path=_path, config_path=config_path)
    # return template
    if _type == 'user':
        filename = '~/.config/systemd/user/rpi2mqtt.service'
    else:
        filename = '/etc/systemd/system/rpi2mqtt.service'

    with open(filename, 'w') as f:
        f.write(template)

if __name__ == '__main__':
    main()