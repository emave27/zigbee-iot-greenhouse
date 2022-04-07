from decimal import Decimal
import threading
import time
import json

from datetime import date, timedelta
import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

#import Flask and turbo_flask to define the server and the socket
from flask import Flask, render_template, request, json
from turbo_flask import Turbo

import mqtt_server

app=Flask(__name__)
turbo=Turbo(app)

#connect to remote dynamodb database
ext_dynamodb=boto3.resource('dynamodb', region_name='eu-west-1')

#deprecated, data is already converted by the Pi script
def convert_interval(value, leftMin, leftMax, rightMin, rightMax):
    leftSpan=leftMax-leftMin
    rightSpan=rightMax-rightMin

    valueScaled=float(value-leftMin)/float(leftSpan)
    newValue=rightMin+(valueScaled*rightSpan)

    return round(newValue, 2)

#get temperature and humidity data from database
def get_data(dynamodb, delta=6):
    if not dynamodb:
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        print('Connected from callback')
    else:
        print('External connection')

    table=dynamodb.Table('GreenhouseData')

    try:
        today=date.today()
        #delta defines how old the data will be: 1 --> yesterday, 7 --> one week ago
        past=today-timedelta(days=delta)
        response = table.query(
            #query the table by using the date key
            KeyConditionExpression=Key('date').eq(str(past)),
            Limit=2, #choose how much date to retrive
            ScanIndexForward=False
        )
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        return response['Items'], past

#function to update settings table
def update_sets(dynamodb, t, d, u, m, f, p, up):
    if not dynamodb:
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        print('Connected from callback')
    else:
        print('External connection')

    table=dynamodb.Table('settings')
    try:
        response=table.update_item(
            Key={
                'user_id': 'admin',
                'set_id': 0
            },
            UpdateExpression="set #th=:t, #dt=:d, #upd=:u, #mod=:m, #fa=:f, #pum=:p, #upl=:up",
            ExpressionAttributeValues={
                ':t': Decimal(t),
                ':d': Decimal(d),
                ':u': Decimal(u),
                ':m': bool(m),
                ':f': f,
                ':p': p,
                ':up': bool(up)
            },
            ExpressionAttributeNames={
                '#th': 'threshold',
                '#dt': 'duty_time',
                '#upd': 'update',
                '#mod': 'mode',
                '#fa': 'fan',
                '#pum': 'pump',
                '#upl': 'upload'
            }
        )

    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        return response

#function to update manual fan/pump stat
def update_manual(dynamodb, f, p):
    if not dynamodb:
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        print('Connected from callback')
    else:
        print('External connection')

    table=dynamodb.Table('settings')
    try:
        response=table.update_item(
            Key={
                'user_id': 'admin',
                'set_id': 1
            },
            UpdateExpression="set #fa=:f, #pum=:p",
            ExpressionAttributeValues={
                ':f': f,
                ':p': p
            },
            ExpressionAttributeNames={
                '#fa': 'fan',
                '#pum': 'pump',
            }
        )

    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        return response

@app.route('/') #render index template
def index():
    return render_template('index.html')

#function to handle datat from the settings form
@app.route('/update_set', methods=['POST'])
def update_set():
    thresh=request.form['temp_t']
    duty=request.form['pump_d']
    update=request.form['up_int']

    mode=request.form['mode']
    fan=True #always true
    pump=True #always true
    upload=request.form['upload']

    print(thresh, duty, update, mode, fan, pump, upload)
    updated=update_sets(ext_dynamodb, thresh, duty, update, int(mode), fan, pump, int(upload))

    return json.dumps({'status':'OK','thresh':thresh,'duty':duty,'update':update,'mode':mode,'fan_stat':fan,'pump_stat':pump,'upload':upload})

#push the fan/pump stat to the raspi using mqtt (manual mode)
@app.route('/handle_manual', methods=['POST'])
def handle_manual():
    fan_stat=request.form['fan_stat']
    pump_stat=request.form['pump_stat']

    updated_set=update_manual(ext_dynamodb, int(fan_stat), int(pump_stat))

    list_set=[int(fan_stat), int(pump_stat)]
    stats=bytearray(list_set)

    #send the stats as a bytearray
    mqtt_server.send_mqtt_message('manual', stats)

    return json.dumps({'status':'OK','fan_stat':fan_stat,'pump_stat':pump_stat})

#function to get current setting on page load
@app.route('/get_set', methods=['POST'])
def get_current_settings(dynamodb=ext_dynamodb):

    if not dynamodb:
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        print('Connected from callback')
    else:
        print('External connection')

    table=dynamodb.Table('settings')

    try:
        #get the settings and the manual fan/pump status
        response=table.get_item(Key={'user_id':'admin', 'set_id':0})
        man_res=table.get_item(Key={'user_id':'admin', 'set_id':1})
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        res=response['Item']
        man=man_res['Item']
    
    temp_t=int(res['threshold'])
    d_time=int(res['duty_time'])
    upd_time=int(res['update'])
    mode=res['mode']
    upload=res['upload']
    fan_stat=man['fan']
    pump_stat=man['pump']

    return json.dumps({'status':'OK','thresh':temp_t,'duty':d_time,'update':upd_time,'mode':mode,'upload':upload, 'fan_stat':fan_stat, 'pump_stat':pump_stat})

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
            time.sleep(20)
            turbo.push(turbo.replace(render_template('loadavg.html'), 'result'))
            #print("clients: ", turbo.clients)

@app.before_first_request
def before_first_request():
    #start the socket as a thread
    threading.Thread(target=update_load).start()