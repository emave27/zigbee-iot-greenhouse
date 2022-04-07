from paho.mqtt import client as paho
import ssl
import struct

conn_flag=False
temp=None
hum=None

def on_connect(client, userdata, flags, rc):
    global conn_flag
    conn_flag=True
    print("Connection returned result: ", str(rc))
    client.subscribe('#', 1)

def on_message(client, userdata, msg):
    global temp
    global hum

    [t, h]=struct.unpack('ff', msg.payload)
    temp=round(t, 2)
    hum=round(h, 2)

mqttc=paho.Client()
mqttc.on_connect=on_connect
mqttc.on_message=on_message


endpoint="a185t3bpm5e89j-ats.iot.eu-west-1.amazonaws.com"
port=8883
ca_path="certs/Amazon-root-CA-1.pem"
cert_path="certs/certificate.pem.crt"
key_path="certs/private.pem.key"

mqttc.tls_set(ca_path, certfile=cert_path, keyfile=key_path, cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2, ciphers=None)

mqttc.connect(endpoint, port, keepalive=300)
mqttc.loop_start()

def pass_data():
    return temp, hum

def send_mqtt_message(topic, message):
    if conn_flag:
        mqttc.publish(topic, message, qos=1)
        print('Message', message, 'sent to topic', topic)
    else:
        print("Waiting for connection")
