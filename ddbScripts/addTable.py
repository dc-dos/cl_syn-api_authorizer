import boto3
import sys

TABLE_NAME = sys.argv[1]
KEY_NAME = sys.argv[2]

# fyi
print(f"Using Account; {boto3.client('sts').get_caller_identity().get('Account')}")

# Create the DynamoDB table.
ddb = boto3.resource('dynamodb')

table = None

try:
    table = ddb.create_table(
        TableName= TABLE_NAME,
        KeySchema=[
            {
                'AttributeName': KEY_NAME,
                'KeyType': 'HASH'
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': KEY_NAME,
                'AttributeType': 'S'
            }
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )
    # Wait until the table exists.
    print("Waiting for table creation....")
    table.meta.client.get_waiter('table_exists').wait(TableName='users')
except Exception as err:
    print(err)

if not table:
    table = ddb.Table(TABLE_NAME)

# Print out some data about the table.
print(f"Items found: {table.item_count}")