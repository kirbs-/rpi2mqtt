import paho.mqtt.publish as mqtt
import paho.mqtt.subscribe as mqtt_sub
from rpi2mqtt.config import config
import traceback


def publish(topic, payload, cnt=1):
    try:
        if cnt <= config.mqtt.retries:
            mqtt.single(topic, payload, hostname=config.mqtt.host, port=config.mqtt.port,
                        auth={'username': config.mqtt.username, 'password': config.mqtt.password},
                        tls={'ca_certs': config.mqtt.ca_cert})
    except:
        traceback.print_exc()
        cnt += 1
        publish(topic, payload, cnt)


def subscribe(topic, callback):
    mqtt_sub.callback(callback, topic, hostname=config.mqtt.host, port=config.mqtt.port,
                        auth={'username': config.mqtt.username, 'password': config.mqtt.password},
                        tls={'ca_certs': config.mqtt.ca_cert})