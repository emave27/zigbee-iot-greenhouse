import boto3
from botocore.exceptions import ClientError

#connect to remote dynamodb database
dynamodb=None
if not dynamodb:
    dynamodb=boto3.resource('dynamodb', region_name='eu-west-1')

#function to upload data
def upload_data_single(date, time, temp, hum, upload):
    if upload: #if upload is true
        try:
            #connect to the table and upload the data
            table=dynamodb.Table('GreenhouseData')
            response=table.put_item(
                Item={
                    'date': date,
                    'time': time,
                    'data':{'temperature': temp,
                            'humidity': hum}
                }
            )
        except ClientError as e:
            print(e.response['Error']['Message'])
        else:
            print("Data uploaded")
    else:
        print("Upload inhibited") #data will not be uploaded

#function to get the settings
def get_settings():
    #connect to the dedicated table
    table=dynamodb.Table('settings')

    try:
        response=table.get_item(Key={'user_id': 'admin', 'set_id':0})
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        res=response['Item']
    
    #filter the values and return them
    temp_t=int(res['threshold'])
    d_time=int(res['duty_time'])
    upd_time=int(res['update'])
    mode=res['mode']
    upload=res['upload']

    return temp_t, d_time, upd_time, mode, upload

def get_manual(depr=True): #deprecated, using mqtt
    if depr:
        print('Deprecated, use mqtt_com.pass_data()')
    else:
        table=dynamodb.Table('settings')

        try:
            response=table.get_item(Key={'user_id': 'admin', 'set_id':1})
        except ClientError as e:
            print(e.response['Error']['Message'])
        else:
            res=response['Item']
        
        fan=res['fan']
        pump=res['pump']

        return fan, pump

#use this function with main_callback script
def upload_data_double(date, time, to_upload, is_temp):
    if is_temp:
        table=dynamodb.Table('GreenhouseDataTemperature')
    
        response=table.put_item(
            Item={
                'date': date,
                'time': time,
                'data':{ 'temperature': to_upload }
            }
        )
        print("Temperature data uploaded")

    else:
        table=dynamodb.Table('GreenhouseDataHumidity')
    
        response=table.put_item(
            Item={
                'date': date,
                'time': time,
                'data':{ 'humidity': to_upload }
            }
        )
        print("Soil humidity data uploaded")

#simple function to convert humidity interval 0-1023 --> 0-100 (percentage)
def convert_interval(value, leftMin, leftMax, rightMin, rightMax):
    leftSpan=leftMax-leftMin
    rightSpan=rightMax-rightMin

    valueScaled=float(value-leftMin)/float(leftSpan)
    newValue=rightMin+(valueScaled*rightSpan)

    return round(newValue, 2)
