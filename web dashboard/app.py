from decimal import Decimal
import threading
import time
import json

from datetime import date, timedelta
import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

from flask import Flask, render_template, request, json
from turbo_flask import Turbo

MIN=360
MAX=1023

app=Flask(__name__)
turbo=Turbo(app)

ext_dynamodb=boto3.resource('dynamodb', region_name='') #add your own region name

def convert_interval(value, leftMin, leftMax, rightMin, rightMax):
    leftSpan=leftMax-leftMin
    rightSpan=rightMax-rightMin

    valueScaled=float(value-leftMin)/float(leftSpan)
    newValue=rightMin+(valueScaled*rightSpan)

    return round(newValue, 2)

def get_data(dynamodb, delta=2):
    if not dynamodb:
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        print('Connected from callback')
    else:
        print('External connection')

    table = dynamodb.Table('GreenhouseData')

    try:
        today = date.today()
        past = today - timedelta(days=delta)
        response = table.query(
            KeyConditionExpression=Key('date').eq(str(past)),
            Limit=2,
            ScanIndexForward=False
        )
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        return response['Items'], past

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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/update_set', methods=['POST'])
def update_set():
    thresh = request.form['temp_t']
    duty = request.form['pump_d']
    update = request.form['up_int']

    mode = request.form['mode']
    fan = True
    pump = True
    upload = request.form['upload']

    print(thresh, duty, update, mode, fan, pump, upload)
    updated=update_data(ext_dynamodb, thresh, duty, update, int(mode), fan, pump, int(upload))
    print(type(updated), updated)

    return json.dumps({'status':'OK','thresh':thresh,'duty':duty,'update':update,'mode':mode,'fan':fan,'pump':pump,'upload':upload})

@app.route('/handle_manual', methods=['POST'])
def handle_manual():
    fan_stat=request.form['fan_stat']
    pump_stat=request.form['pump_stat']

    updated_set=update_manual(ext_dynamodb, int(fan_stat), int(pump_stat))
    print(int(fan_stat), int(pump_stat))

    return json.dumps({'status':'OK','fan_stat':fan_stat,'pump_stat':pump_stat})
@app.route('/get_set', methods=['POST']) #get current setting on page load
def get_current_settings(dynamodb=ext_dynamodb):

    if not dynamodb:
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        print('Connected from callback')
    else:
        print('External connection')

    table=dynamodb.Table('settings')

    try:
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
def update_fromDynamoDB():
    data=get_data(ext_dynamodb)

    print("Get succeeded")
    t_result=[]
    h_result=[]

    for d in data:
        temp=d['data']['temperature']
        hum=d['data']['humidity']
        temp=float(temp)
        hum=int(hum)
        t_result.append(round(temp, 2))
        h_result.append(convert_interval(hum, MAX, MIN, 100, 0))
    
    #push only the last value
    result=[t_result[-1], h_result[-1]]
    #print(t_result, h_result)

    return {'val1': result[0], 'val2': result[1]}

def update_load():
    with app.app_context():
        while True:
            time.sleep(300)
            turbo.push(turbo.replace(render_template('loadavg.html'), 'result'))
            #print("clients: ", turbo.clients)

@app.before_first_request
def before_first_request():
    threading.Thread(target=update_load).start()
