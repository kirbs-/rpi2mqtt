import paho.mqtt.publish as mqtt
# import paho.mqtt.subscribe as mqtt_sub
from paho.mqtt.client import Client
from rpi2mqtt.config import config
import traceback


def publish(topic, payload, cnt=1):
    try:
        if cnt <= config.mqtt.retries:
            mqtt.single(topic, payload, hostname=config.mqtt.host, port=config.mqtt.port,
                        auth={'username': config.mqtt.username, 'password': config.mqtt.password},
                        tls={'ca_certs': config.mqtt.ca_cert},
                        retain=True)
    except:
        traceback.print_exc()
        cnt += 1
        publish(topic, payload, cnt)


class MqttClient(object):
    __shared_state = {}

    def __init__(self):
        self.__dict__ = self.__shared_state
        self.client = Client('rpi2mqtt')
        self.subscribed_topics = {}

    def setup(self):
        self.client.tls_set(ca_certs=config.mqtt.ca_cert) #, certfile=None, keyfile=None, cert_reqs=cert_required, tls_version=tlsVersion)

        # if args.insecure:
        #     self.client.tls_insecure_set(True)

        if config.mqtt.username or config.mqtt.password:
            self.client.username_pw_set(config.mqtt.username, config.mqtt.password)

        print("Connecting to " + config.mqtt.host + " port: " + str(config.mqtt.port))
        self.client.connect(config.mqtt.host, config.mqtt.port, 60)
        # mqttc.subscribe(args.topic, args.qos)

        self.client.loop_start()

        self.client.on_subscribe = self.on_subscribe
        self.client.on_message = self.on_message

    def on_message(selfm, mqttc, obj, msg):
        print(msg.topic + " " + str(msg.qos) + " " + str(msg.payload))

    def on_subscribe(self, mqttc, obj, mid, granted_qos):
        print("Subscribed: " + str(mid) + " " + str(granted_qos))

    def subscribe(self, topic, callback):
        self.client.subscribe(topic)
        self.client.message_callback_add(topic, callback)
        # mqtt_sub.callback(callback, topic, hostname=config.mqtt.host, port=config.mqtt.port,
        #                   auth={'username': config.mqtt.username, 'password': config.mqtt.password},
        #                   tls={'ca_certs': config.mqtt.ca_cert})
