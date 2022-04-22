from paho.mqtt import client as paho
import ssl
import struct

class ServerMQTT():
    def __init__(self):
        self.conn_flag=False
        self.temp=None
        self.hum=None

        def on_connect(client, userdata, flags, rc):
            self.conn_flag=True
            if int(rc)==0:
                print('Connection successful')
                client.subscribe('sensors', 1)
            else:
                print('Connection error:', str(rc))

        def on_message(client, userdata, msg):
            [t, h]=struct.unpack('ff', msg.payload)
            self.temp=round(t, 2)
            self.hum=round(h, 2)

        self.mqttc=paho.Client()
        self.mqttc.on_connect=on_connect
        self.mqttc.on_message=on_message

        ca_path="certs/"
        cert_path="certs/"
        key_path="certs/"

        self.mqttc.tls_set(ca_path, certfile=cert_path, keyfile=key_path, cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2, ciphers=None)
    
    def connect(self):
        endpoint="your endpoint"
        port=8883

        self.mqttc.connect(endpoint, port, keepalive=600)
        self.mqttc.loop_start()

    def pass_data(self):
        return self.temp, self.hum

    def send_mqtt_message(self, topic, message):
        if self.conn_flag:
            self.mqttc.publish(topic, message, qos=1)
            print('Message sent to topic', topic)
        else:
            print("Waiting for connection")
    
    def on_keyboardinterrupt(self):
        self.mqttc.disconnect()
        self.mqttc.loop_stop()
        print('Loop stopped by keyboardinterrupt')
