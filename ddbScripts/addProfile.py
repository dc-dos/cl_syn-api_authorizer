import boto3
import json
import datetime as DT

# Testing only!!!
API_KEY = "BullwinkleJMoose"

# fyi
print(f"Using Account; {boto3.client('sts').get_caller_identity().get('Account')}")

ddb = boto3.resource('dynamodb')
table = ddb.Table("cl_ssi-authorizer_profiles")
"""
table.put_item(
    Item={
        "api_key": API_KEY,
        "name": "DD888's",
        "api_permits": {
            "GET": ["/api/csi"],
            "POST": ["/api/csi"]
        },
        "created_at": DT.datetime.now().strftime("%Y-%m-%d %H:%M:%S %z")
    }
)
"""
# read it back
print(API_KEY)
response = table.get_item(
    Key={
        "api_key": API_KEY,
    }
)
print(response)

# and report
item = response['Item']
print(f'Saved item: {json.dumps(item)}')