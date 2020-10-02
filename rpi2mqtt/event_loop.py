# import asyncio
from rpi2mqtt.config import config, save
from rpi2mqtt.binary import *
from rpi2mqtt.temperature import *
from rpi2mqtt.ibeacon import Scanner
from rpi2mqtt.switch import Switch
from rpi2mqtt.thermostat import HestiaPi
import time
import rpi2mqtt.mqtt as mqtt
from beacontools import BeaconScanner, IBeaconFilter
import traceback
import logging
import sys
import argparse


parser = argparse.ArgumentParser()

parser.add_argument("-c", "--config",
                help="Path to config.yaml")


def main():
    logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

    args = parser.parse_args() 

    if args.config:
        save(args.config)

    # start MQTT client
    mqtt.setup()

    sensor_list = []

    for sensor in config.sensors:
        if sensor.type == 'dht22':
            s = DHT(sensor.pin, sensor.topic, sensor.name, 'sensor', sensor.type)
        elif sensor.type == 'ibeacon':
            s = Scanner(sensor.name, sensor.topic, sensor.uuid, sensor.away_timeout)
        elif sensor.type == 'switch':
            s = Switch(sensor.name, sensor.pin, sensor.topic)
        elif sensor.type == 'reed':
            s = ReedSwitch(sensor.name, sensor.pin, sensor.topic, sensor.normally_open, sensor.get('device_type'))
        elif sensor.type == 'bme280':
            s = BME280(sensor.name, sensor.topic)
        elif sensor.type == 'hestiapi':
            s = HestiaPi(sensor.name, sensor.topic, sensor.heat_point, sensor.cool_point, sensor.set_point_tolerance, sensor.min_run_time)
        else:
            logging.warn('Sensor {} found in config, but was not setup.'.format(sensor.name))
        if s:
            sensor_list.append(s)

    try:
        scanner = BeaconScanner(sensor_list[1].process_ble_update)
        scanner.start()
    except:
        logging.error("Beacon scanner did not start")

    try:
        while True:

            for sensor in sensor_list:
                # if type(sensor) == Switch:
                #     sensor.callback('a', 'b', {'payload': 'n/a'})
                # else:
                sensor.callback()

            time.sleep(300)

    except:
        traceback.print_exc()
        scanner.stop()
        mqtt.client.loop_stop()


if __name__ == '__main__':
    main()