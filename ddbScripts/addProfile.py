import boto3
import json

# fyi
print(f"Using Account; {boto3.client('sts').get_caller_identity().get('Account')}")

ddb = boto3.resource('dynamodb')

table = ddb.Table("cl_ssi-authorizer_api")

table.put_item(
    Item={
        "api_id": "myapikey",
        "orgid": "42",
        "orgname": "DOS World",
        "api_permits": {
            "GET": ["/rest/endpoint1","/rest/endpoint1"],
            "POST": []
        }
    }
)

response = table.get_item(
    Key={
        "api_id": "myapikey",
    }
)
item = response['Item']
print(f'Saved item: {json.dumps(item)}')