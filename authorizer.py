"""
authorizer.py

dconnell
3/10/20

Use API_KEY sent with request (Authorization Header) to lookup and validate the
sender. If validated, the methodArn / API_KEY is authorized (or not).

Notes:

- The Authorization Token (retrieved from the Authorization header in the request),
is made up of a Base64 encoded string that contains the encrytped api_key and the 
nonce from the ChaCha20_Poly80 cipher that encrypted the api_key delimited by a colon.

    format: b64(<api_key>:<nonce>)

"""
import os
from Crypto.Cipher import ChaCha20_Poly1305 as ChaCha
from Crypto.Random import get_random_bytes
from base64 import b64encode, b64decode

DDB_TABLE = os.environ['DDB_TABLE']

AWSPolicy = {
    "principalId": '*',
    "Version": "2012-10-17",
    "Statement": [
        {
        "Action": "execute-api:Invoke",
        "Effect": "Deny",
        "Resource": None
        }
    ],
    "context": {}
}

class ReqAuthorizer(object):
    """
    """
    def __init__(self, event):
        self.token = event['authorizationToken']
        self.resource = event['methodArn']
        self.cypher_key = os.environ['CYPHER_KEY'].encode("utf8")
        self.api_key = None
        
    def validate(self):
        "Attempt to decrypt the token"
        try:
            # split out api_key, nonce
            str_token = b64decode(self.token)
            nonce, ct = str_token.split(":")
            # decrypt the token
            cha = ChaCha.new(key = self.cypher_key, nonce=nonce)
            # save the api_key for customer lookup
            self.api_key = cha.decrypt(ct).decode('utf8')           
        except Exception as err:
            # whatever, it aint good
            print(f"Validation Excetion: {err}")
            return False
        
        # ok, token was valid
        return True

    def getProfile(self):
        """
        Attempt to retrieve client profile using
        token data.
        """
        # get service connection
        ddb = boto3.resource('dynamodb')

        # query ddb
        response = ddb.Table(DDB_TABLE).get_item(
            Key={
                "api_id": self.api_key,
                }
        )

        profile = response['Item']
        print(f'Retrieved Profile: {json.dumps(self.profile)}')
        return profile

    def doAuth(self):
        """
        Make call into DDB using the key/secret
        to access the customer profile and set
        up user / store # data
        """
        # approve access
        try: 
            prof = self.getProfile()
            parts = self.resource.split("/")
            verb = parts[2]
            endpt = parts[3:].join("/")
            for tst in prof['permits'][verb]:
                if tst == endpt:
                    AWSPolicy['policyDocument']['Statement']['Effect'] = 'Allow'
                    break
        except Exception as err:
            print(f'Auth Exception: {err}')

    def run(self):
        if self.validate():
            doAuth()
        return  AWSPolicy

def handler(event, context):
    "Evaluate access request from outside"
    # prep policy statement
    stmnt = AWSPolicy['policyDocument']['Statement']
    stmnt["Resource"] = event['methodArn']

    # validate and auth check
    return ReqAuthorizer(event).run()