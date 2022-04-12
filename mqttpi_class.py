import paho.mqtt.client as paho
import ssl
import struct

class PiMQTT():
    def __init__(self):
        self.conn_flag=False
        self.got_message=False
        self.got_mode_message=False

        self.fan_s=False
        self.pump_s=False
        self.mode=True

        #subscribe to multiple topics
        TOPICS=[('manual', 1), ('mode', 1)]

        #on_connect callback
        def on_connect(client, userdata, flags, rc):
            if int(rc)==0:
                print('Connection successful')
            else:
                print('Connection error:', str(rc))
            self.conn_flag=True
            client.subscribe(TOPICS)

        #on_message callback
        def on_message(client, userdata, msg):
            #filter the message using message topic
            if msg.topic=='manual':
                #unpack the message, from byte to int
                [f, p]=struct.unpack('ii', msg.payload)
                self.fan_s=bool(f)
                self.pump_s=bool(p)

                self.got_message=True
            else:
                m=int(msg.payload)
                self.mode=bool(m)

                self.got_mode_message=True

        #define the client and add the callbacks
        self.mqttc=paho.Client()
        self.mqttc.on_connect=on_connect
        self.mqttc.on_message=on_message

        #define the endpoints, the port and the certificate paths
        endpoint="your-endpoint"
        port=8883 #default port
        ca_path="certs/"
        cert_path="certs/"
        key_path="certs/"

        #set the certificate and the key files
        self.mqttc.tls_set(ca_path, certfile=cert_path, keyfile=key_path, cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2, ciphers=None)

        #connect to the endpoint and start the loop
        self.mqttc.connect(endpoint, port, keepalive=1860)
        self.mqttc.loop_start()

    #pass the data to the main loop
    def pass_data(self):
        if self.got_message:
            return self.fan_s, self.pump_s
        else:
            return False, False
    
    #pass the mode value to the main loop
    def pass_mode(self):
        if self.got_mode_message:
            return self.mode
        else:
            return True

    #publish the message to adefined topic
    def send_message(self, topic, message):
        if self.conn_flag:
            self.mqttc.publish(topic, message, qos=1)
            print('Message sent to topic:', topic)
        else:
            print('Waiting for connection')
    
    #handle keyboardinterrupt event
    def on_keyboardinterrupt(self):
        self.mqttc.disconnect()
        self.mqttc.loop_stop()
        print('Loop stopped by KeyboardInterrupt')
