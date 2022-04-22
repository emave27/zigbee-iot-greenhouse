from decimal import Decimal
from datetime import date, timedelta
import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key

class DynamoUtils():
    def __init__(self):
        self.dynamodb=boto3.resource('dynamodb', region_name='your-region')

    #deprecated, data is already converted by the Pi script
    def convert_interval(self, value, leftMin, leftMax, rightMin, rightMax):
        leftSpan=leftMax-leftMin
        rightSpan=rightMax-rightMin

        valueScaled=float(value-leftMin)/float(leftSpan)
        newValue=rightMin+(valueScaled*rightSpan)

        return round(newValue, 2)

    #get temperature and humidity data from database
    def get_data(self, delta=2, limit=10):
        table=self.dynamodb.Table('GreenhouseData')

        try:
            today=date.today()
            #delta defines how old the data will be: 1 --> yesterday, 7 --> one week ago
            past=today-timedelta(days=delta)
            response = table.query(
                #query the table by using the date key
                KeyConditionExpression=Key('date').eq(str(past)),
                #KeyConditionExpression=Key('date').between(str(today), str(past)),
                Limit=limit, #choose how much data retrive
                ScanIndexForward=False
            )
        except ClientError as e:
            print(e.response['Error']['Message'])
        else:
            return response['Items']

    #function to update settings table
    def update_sets(self, tt, ht, d, u, no, up):
        table=self.dynamodb.Table('settings')
        
        try:
            response=table.update_item(
                Key={'user_id': 'admin', 'set_id': 0},
                UpdateExpression="set #tth=:tt, #uth=:ut, #dt=:d, #upd=:u, #upl=:up, #notf=:no, #mod=:m",
                ExpressionAttributeValues={
                    ':tt': Decimal(tt),
                    ':ut': Decimal(ht),
                    ':d': Decimal(d),
                    ':u': Decimal(u),
                    ':m': True,
                    ':no': bool(no),
                    ':up': bool(up)
                },
                ExpressionAttributeNames={
                    '#tth': 'temp_threshold',
                    '#uth': 'hum_threshold',
                    '#dt': 'duty_time',
                    '#upd': 'update',
                    '#mod': 'mode',
                    '#notf': 'notifications',
                    '#upl': 'upload'
                }
            )

        except ClientError as e:
            print(e.response['Error']['Message'])
        else:
            return response
    
    def update_mode(self, mode):
        table=self.dynamodb.Table('settings')
        
        try:
            response=table.update_item(
                Key={
                    'user_id': 'admin',
                    'set_id': 0
                },
                UpdateExpression='set  #mod=:m',
                ExpressionAttributeValues={
                    ':m': bool(mode)
                },
                ExpressionAttributeNames={
                    '#mod': 'mode'
                }
            )

        except ClientError as e:
            print(e.response['Error']['Message'])
        else:
            return response

    #function to update manual fan/pump stat
    def update_manual(self, f, p):
        table=self.dynamodb.Table('settings')
        
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
