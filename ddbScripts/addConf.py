import boto3
import json
import datetime as DT
import os

print(os.environ["AWS_PROFILE"])

# fyi
print(f"Using Account; {boto3.client('sts').get_caller_identity().get('Account')}")

ddb = boto3.resource('dynamodb')
table = ddb.Table("cl_syn-csi_configs")

item={
    "app_id": "csigwx1",
    "name": "CSI Warehouse",
    "db": {
        "host": "",
        "port": 5432,
        "database": "gwx1",
        "user": "david",
        "password": ""
    },
    "created_at": DT.datetime.now().strftime("%Y-%m-%d %H:%M:%S %z")
    }

table.put_item(Item=item)

# read it back
print(item['app_id'])
response = table.get_item(
    Key={
        "app_id": item['app_id'],
    }
)

print(response)

# and report
item = response['Item']
print(f'Saved item: {json.dumps(item)}')