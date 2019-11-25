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


def main():
    sensor_list = []

    for sensor in config.sensors:
        if sensor.type == 'dht22':
            s = DHT(sensor.pin, sensor.topic, sensor.name, 'sensor', sensor.type)
        elif sensor.type == 'ibeacon':
            s = Scanner(sensor.name, sensor.topic, sensor.uuid, sensor.away_timeout)
        elif sensor.type == 'switch':
            s = Switch(sensor.pin, sensor.name, sensor.topic)

        sensor_list.append(s)

    scanner = BeaconScanner(sensor_list[1].process_ble_update)
    scanner.start()

    # start MQTT client
    mc = mqtt.MqttClient()
    mc.setup()

    try:
        while True:

            for sensor in sensor_list:
                if sensor.type == 'switch':
                    sensor.callback('a', 'b', {'payload': 'n/a'})
                else:
                    sensor.callback()

            time.sleep(300)

    except:
        traceback.print_exc()
        scanner.stop()
        mc.client.loop_stop()


if __name__ == '__main__':
    main()