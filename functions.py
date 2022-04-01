import boto3
from botocore.exceptions import ClientError

dynamodb=None
if not dynamodb:
    dynamodb=boto3.resource('dynamodb', region_name='')

def upload_data_single(date, time, temp, hum, upload):
    if upload:
        try:
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
        print("Upload inhibited")
        
def get_settings():
    table=dynamodb.Table('settings')

    try:
        response=table.get_item(Key={'user_id': '', 'set_id':})
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        res=response['Item']
    
    temp_t=int(res['threshold'])
    d_time=int(res['duty_time'])
    upd_time=int(res['update'])
    mode=res['mode']
    fan=res['fan']
    pump=res['pump']
    upload=res['upload']

    return temp_t, d_time, upd_time, mode, fan, pump, upload

def upload_data(date, time, to_upload, is_temp):
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


def convert_interval(value, leftMin, leftMax, rightMin, rightMax):
    leftSpan=leftMax-leftMin
    rightSpan=rightMax-rightMin

    valueScaled=float(value-leftMin)/float(leftSpan)
    newValue=rightMin+(valueScaled*rightSpan)

    return round(newValue, 2)
