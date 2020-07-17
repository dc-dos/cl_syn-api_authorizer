import boto3
import json
import datetime as DT
import os

print(os.environ["AWS_PROFILE"])

# fyi
print(f"Using Account; {boto3.client('sts').get_caller_identity().get('Account')}")

ddb = boto3.resource('dynamodb')
table = ddb.Table("cl_ssi-authorizer_profiles")

item={
    "api_key": "563da6dd5730d8c268cc14c6ef87bb3d",
    "name": "Pepsico",
    "access_tokens": ["f9cd780f8e680b9ae423b3afe6cbfb94"],
    "worx_url": "http://test3.rlsworx.com/Mobility/go.mbl",
    "gwxid": "18621",
    "api_permits": {
        "GET": ["/api/csi"],
    },
    "created_at": DT.datetime.now().strftime("%Y-%m-%d %H:%M:%S %z")
    }

table.put_item(Item=item)

# read it back
print(item['api_key'])
response = table.get_item(
    Key={
        "api_key": item['api_key'],
    }
)
print(response)

# and report
item = response['Item']
print(f'Saved item: {json.dumps(item)}')