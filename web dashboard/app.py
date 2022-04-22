from socket import socket
from threading import Thread
from time import sleep
import struct
import atexit

#import Flask and turbo_flask to handle server and socket
from flask import Flask, render_template, request, json
from turbo_flask import Turbo
from botocore.exceptions import ClientError

from mqttserver_class import ServerMQTT
from dynamodb_utils import DynamoUtils

MIN=360
MAX=1023

app=Flask(__name__)
turbo=Turbo(app)
mqtt_server=ServerMQTT()
dynautils=DynamoUtils()

def on_interrupt():
    print(' pressed')
    mqtt_server.on_keyboardinterrupt()
    print('Server stopped')

atexit.register(on_interrupt)

@app.route('/') #render index template
def index():
    return render_template('index.html')

@app.route('/get_data', methods=['POST'])
def get_data_fromdb():
    shift=int(request.get_data())
    #res will be a list of dicts
    res=dynautils.get_data(shift, 20)
    #invert the list to sort the data from oldest to newest
    res.reverse()

    c=[] #times ('clock')
    t=[] #temps
    h=[] #humidity (unconverted)

    for d in res: #extract the data from the dicts and pack them in lists
        tt=float(d['data']['temperature']) #from decimal to float
        ht=int(d['data']['humidity']) #from decimal to int

        c.append(d['time'].replace('-', ':')) #replace - with : in time string
        t.append(round(tt, 2)) #round to two decimal digit
        h.append(dynautils.convert_interval(ht, MAX, MIN, 0, 100)) #use convert_interval() to convert value to 0-100 range

    return json.dumps({'status':'OK','time':c,'temperature':t,'humidity':h})

#function to handle data from the settings form
@app.route('/update_set_fromdash', methods=['POST'])
def update_set_fromdash():
    temp_thresh=request.form['temp_t']
    hum_thresh=request.form['hum_t']
    duty=request.form['pump_d']
    update=request.form['up_int']
    #mode=request.form['mode']
    upload=request.form['upload']
    
    #print(temp_thresh, hum_thresh, duty, update, mode, upload)
    updated=dynautils.update_sets(temp_thresh, hum_thresh, duty, update, int(upload)) #int(mode),

    return json.dumps({'status':'OK','temp_thresh':temp_thresh,'hum_thresh':hum_thresh,'duty':duty,'update':update,'upload':upload}) #'mode':mode,

@app.route('/update_mode_fromdash', methods=['POST'])
def update_mode_fromdash():
    mode_byte=request.get_data()
    mode_int=int(request.get_data())

    #dynautils.update_mode(mode_int)
    mqtt_server.send_mqtt_message('mode', mode_byte)

    return json.dumps({'status':'OK'})

#push the fan/pump stat to the raspi using mqtt (manual mode)
@app.route('/handle_manual', methods=['POST'])
def handle_manual():
    fan_stat=request.form['fan_stat']
    pump_stat=request.form['pump_stat']

    updated_set=dynautils.update_manual(int(fan_stat), int(pump_stat))

    #pack the data as byte (datatype accepted by mqtt publish method)
    stats=struct.pack('ii', int(fan_stat), int(pump_stat))
    mqtt_server.send_mqtt_message('manual', stats)

    return json.dumps({'status':'OK','fan_stat':fan_stat,'pump_stat':pump_stat})

#function to get current setting on page load
@app.route('/get_set', methods=['POST'])
def get_current_settings():
    table=dynautils.dynamodb.Table('settings')

    try:
        response=table.get_item(Key={'user_id':'admin', 'set_id':0})
        man_res=table.get_item(Key={'user_id':'admin', 'set_id':1})
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        res=response['Item']
        man=man_res['Item']
    
    temp_thresh=int(res['temp_threshold'])
    hum_thresh=int(res['hum_threshold'])
    d_time=int(res['duty_time'])
    upd_time=int(res['update'])
    mode=res['mode']
    upload=res['upload']
    notify=res['notifications']
    fan_stat=man['fan']
    pump_stat=man['pump']

    return json.dumps({'status':'OK','temp_thresh':temp_thresh,'hum_thresh':hum_thresh,'duty':d_time,'update':upd_time,'mode':mode,'upload':upload,'notify':notify,'fan_stat':fan_stat, 'pump_stat':pump_stat})

@app.context_processor
def update_fromMQTT():
    #get data from mqtt topic
    t, h=mqtt_server.pass_data()
    result=[t, h]

    return {'val1': result[0], 'val2': result[1]}

def update_load():
    with app.app_context():
        while True:
            #push new data to the client every n seconds using turbo.push()
            sleep(30)
            turbo.push(turbo.replace(render_template('loadavg.html'), 'result'))

@app.before_first_request
def before_first_request():
    #connect to mqtt server only on request
    mqtt_server.connect()
    #start the socket as a thread
    socket_thread=Thread(target=update_load, daemon=True)
    socket_thread.start()
