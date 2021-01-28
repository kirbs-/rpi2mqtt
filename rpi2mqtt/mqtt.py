import paho.mqtt.publish as mqtt
# import paho.mqtt.subscribe as mqtt_sub
from paho.mqtt.client import Client
from rpi2mqtt.config import Config
# import traceback
import logging
# import sys


# logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
class Client():
    
    client = None
    subscribed_topics = None
    config = None

    @classmethod
    def publish(cls, topic, payload, cnt=1):
        try:
            logging.info("Pushlishing to topic {}: | attempt: {} | message: {}".format(topic, cnt, payload))
            if cnt <= cls.config.mqtt.retries:
                mqtt.single(topic, payload, 
                            hostname=cls.config.mqtt.host, 
                            port=cls.config.mqtt.port,
                            auth={'username': cls.config.mqtt.username, 'password': cls.config.mqtt.password},
                            tls={'ca_certs': cls.config.mqtt.ca_cert},
                            retain=True)
        except Exception as e:
            logging.exception("Error publishing message.", e)
            cnt += 1
            cls.publish(topic, payload, cnt)

    @classmethod
    def setup(cls):
        cls.client = Client()
        cls.subscribed_topics = {}
        cls.config = Config.get_instance()
        cls.client.tls_set(ca_certs=cls.config.mqtt.ca_cert) #, certfile=None, keyfile=None, cert_reqs=cert_required, tls_version=tlsVersion)

        # if args.insecure:
        #     self.client.tls_insecure_set(True)

        if cls.config.mqtt.username or cls.config.mqtt.password:
            cls.client.username_pw_set(cls.config.mqtt.username, cls.config.mqtt.password)

        logging.info("Connecting to " + cls.config.mqtt.host + " port:" + str(cls.config.mqtt.port))
        cls.client.connect(cls.config.mqtt.host, cls.config.mqtt.port, 60)
        logging.info("Successfully connected to {} port:{}".format(cls.config.mqtt.host, str(cls.config.mqtt.port)))

        cls.client.loop_start()

        cls.client.on_subscribe = Client.on_subscribe
        cls.client.on_message = on_message

    @staticmethod
    def on_message(mqttc, obj, msg):
        logging.info("Recieved: " + msg.topic + " " + str(msg.qos) + " " + str(msg.payload))

    @staticmethod
    def on_subscribe(mqttc, obj, mid, granted_qos):
        logging.info("Subscribed to " + str(mid) + " " + str(granted_qos))

    @classmethod
    def subscribe(cls, topic, callback):
        logging.info("Subscribing to topic %s", topic)
        res = cls.client.subscribe(topic)
        logging.info('Subscription result = {}'.format(res))
        cls.client.message_callback_add(topic, callback)
        return res
