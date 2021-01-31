import logging
import sys
logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

from rpi2mqtt.mqtt import MQTT 
import time


def main():
    logging.debug('debug message')
    logging.info('info message')
    logging.warning('warning')
    logging.error('error')
    MQTT.setup()

def test_mqtt_subscribe():
    MQTT.setup()

    def callback(client, data, message):
        print(message.payload)

    while True:
        res, id = MQTT.subscribe('hello', callback)
        if res == 0:
            break
        time.sleep(1)

    while True:
        pass
        # mqtt.setup()

if __name__ == '__main__':
    # logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
    test_mqtt_subscribe()
