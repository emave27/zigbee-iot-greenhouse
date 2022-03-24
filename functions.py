import boto3

dynamodb=None
if not dynamodb:
    dynamodb=boto3.resource('dynamodb', region_name='')

def upload_data_single(date, time, temp, hum):
    print("todo")

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
