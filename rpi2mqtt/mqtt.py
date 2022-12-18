import paho.mqtt.publish as _mqtt
# import paho.mqtt.subscribe as mqtt_sub
from paho.mqtt.client import Client
from rpi2mqtt.config import Config
# import traceback
import logging
# import sys
import pendulum


# logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)


def on_message(mqttc, obj, msg):
    logging.info("Recieved: " + msg.topic + " " + str(msg.qos) + " " + str(msg.payload))


def on_subscribe(mqttc, obj, mid, granted_qos):
    logging.info("Subscribed to " + str(mid) + " " + str(granted_qos))


class Subscription():
    def __init__(self, topic, callback):
        self.topic = topic
        self.callback = callback
        self.last_ping = pendulum.now()


class MQTT():
    
    client = None
    subscribed_topics = None
    config = None

    @classmethod
    def publish(cls, topic, payload, cnt=1):
        try:
            logging.debug("Pushlishing to topic {}: | attempt: {} | message: {}".format(topic, cnt, payload))
            if cnt <= cls.config.mqtt.retries:
                if payload == 'pong':
                    cls.subscribed_topics[topic].last_ping = pendulum.now()

                _mqtt.single(topic, payload, 
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

        cls.client.on_subscribe = on_subscribe
        cls.client.on_message = on_message



    @classmethod
    def subscribe(cls, topic, callback):
        logging.info("Subscribing to topic %s", topic)
        res = cls.client.subscribe(topic)
        logging.debug('Subscription result = {}'.format(res))
        cls.client.message_callback_add(topic, callback)
        cls.subscribed_topics[topic] = Subscription(topic, callback)
        return res

    @classmethod
    def ping_subscriptions(cls):
        for topic, sub in cls.subscribed_topics.items():
            logging.debug("Checing subcription status on topic {}".format(topic))
            response = MQTT.publish(topic, "ping")
            last_seen = pendulum.now() - cls.subscribed_topics[topic].last_ping
            if last_seen and last_seen.seconds > cls.config.polling_interval * 2:
                logging.warn("Not subscribed to topic {}. Resubscribing...".format(topic))
                MQTT.subscribe(topic, sub.callback)

    @classmethod
    def refresh_subscriptions(cls):
        for topic, sub in cls.subscribed_topics.items():
            MQTT.client.unsubscribe(topic)
            MQTT.subscribe(sub.topic, sub.callback)

    @staticmethod
    def pongable(func):
        # def decorator_wrapper(func):
        def wrapper(self, client, userdata, message):
            logging.debug('Received message {} on topic {}'.format(message.payload.decode(), message.topic))
            payload = message.payload.decode()
            if payload == 'ping':
                MQTT.publish(message.topic, "pong") 
                return
            elif payload == 'pong':
                return
            return func(self, client, userdata, message)
        return wrapper
        # return decorator_wrapper