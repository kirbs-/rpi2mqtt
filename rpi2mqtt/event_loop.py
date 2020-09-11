# import asyncio
from rpi2mqtt.config import config
import RPi.GPIO as GPIO
from rpi2mqtt.binary import *
from rpi2mqtt.temperature import *
from rpi2mqtt.ibeacon import Scanner
from rpi2mqtt.switch import Switch
import time
import rpi2mqtt.mqtt as mqtt
from beacontools import BeaconScanner, IBeaconFilter
import traceback
import logging


logging.basicConfig(level=logging.INFO)


def main():
    # start MQTT client
    mqtt.setup()
    print('Event loop client: %s', mqtt.client)

    sensor_list = []

    for sensor in config.sensors:
        if sensor.type == 'dht22':
            s = DHT(sensor.pin, sensor.topic, sensor.name, 'sensor', sensor.type)
        elif sensor.type == 'ibeacon':
            s = Scanner(sensor.name, sensor.topic, sensor.uuid, sensor.away_timeout)
        elif sensor.type == 'switch':
            s = Switch(sensor.pin, sensor.name, sensor.topic)
        elif sensor.type == 'reed':
            s = ReedSwitch(sensor.pin, sensor.topic, sensor.name, sensor.normally_open)

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