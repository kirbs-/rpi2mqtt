import paho.mqtt.publish as mqtt
# import paho.mqtt.subscribe as mqtt_sub
from paho.mqtt.client import Client
from rpi2mqtt.config import config
import traceback
import logging
import sys


# logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
client = Client()
subscribed_topics = {}


def publish(topic, payload, cnt=1):
    try:
        logging.info("Pushlishing to topic {}: | attempt: {} | message: {}".format(topic, cnt, payload))
        if cnt <= config.mqtt.retries:
            mqtt.single(topic, payload, 
                        hostname=config.mqtt.host, 
                        port=config.mqtt.port,
                        auth={'username': config.mqtt.username, 'password': config.mqtt.password},
                        tls={'ca_certs': config.mqtt.ca_cert},
                        retain=True)
    except Exception as e:
        logging.exception("Error publishing message.", e)
        cnt += 1
        publish(topic, payload, cnt)


def setup():
    global client
    client.tls_set(ca_certs=config.mqtt.ca_cert) #, certfile=None, keyfile=None, cert_reqs=cert_required, tls_version=tlsVersion)

    # if args.insecure:
    #     self.client.tls_insecure_set(True)

    if config.mqtt.username or config.mqtt.password:
        client.username_pw_set(config.mqtt.username, config.mqtt.password)

    logging.info("Connecting to " + config.mqtt.host + " port:" + str(config.mqtt.port))
    client.connect(config.mqtt.host, config.mqtt.port, 60)
    logging.info("Successfully connected to {} port:{}".format(config.mqtt.host, str(config.mqtt.port)))

    client.loop_start()

    client.on_subscribe = on_subscribe
    client.on_message = on_message


def on_message(mqttc, obj, msg):
    logging.info("Recieved: " + msg.topic + " " + str(msg.qos) + " " + str(msg.payload))


def on_subscribe(mqttc, obj, mid, granted_qos):
    logging.info("Subscribed to " + str(mid) + " " + str(granted_qos))


def subscribe(topic, callback):
    global client
    logging.info("Subscribing to topic %s", topic)
    res = client.subscribe(topic)
    logging.info('Subscription result = {}'.format(res))
    client.message_callback_add(topic, callback)
    return res
