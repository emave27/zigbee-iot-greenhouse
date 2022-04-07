import paho.mqtt.client as paho
import ssl

fan_s=None
pump_s=None

conn_flag=False

#on_connect callback
def on_connect(client, userdata, flags, rc):
    global conn_flag
    print("Connection returned result: ", str(rc))
    conn_flag=True
    client.subscribe("#" , 1)

#on_message callback
def on_message(client, userdata, msg):
    global fan_s
    global pump_s

    pay_load=msg.payload
    
    #covert the message: byte --> int --> bool
    fan_s=bool(int.from_bytes(pay_load[:1], byteorder='big', signed=False))
    pump_s=bool(int.from_bytes(pay_load[-1:], byteorder='big', signed=False))

#define new client and add the callbacks
mqttc=paho.Client()
mqttc.on_connect=on_connect
mqttc.on_message=on_message

#define the endpoint, the port and the certificate paths
endpoint="a185t3bpm5e89j-ats.iot.eu-west-1.amazonaws.com"
port=8883
ca_path="certs/Amazon-root-CA-1.pem"
cert_path="certs/certificate.pem.crt"
key_path="certs/private.pem.key"

#set the certificate and the key file
mqttc.tls_set(ca_path, certfile=cert_path, keyfile=key_path, cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2, ciphers=None)

#connect to the endpoint and start the loop
mqttc.connect(endpoint, port, keepalive=300)
mqttc.loop_start()

#pass the data to the main script
def pass_data():
    return fan_s, pump_s

#publish message to a defined topic
def send_message(topic, message):
    if conn_flag:
        mqttc.publish(topic, message, qos=1)
        print('Message', message, 'sent to topic', topic)
    else:
        print('Waiting or connection')

#handle KeyboardInterrupt
def on_keyboardinterrupt():
    mqttc.disconnect()
    mqttc.loop_stop()
    print('Loop stopped by KeyboardInterrupt')
    quit()