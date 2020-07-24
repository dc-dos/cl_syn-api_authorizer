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
import json
from base64 import b64encode, b64decode
import boto3

DDB_TABLE = os.environ['DDB_TABLE']

AWSPolicy = {
  "principalId": "*", 
  "policyDocument": {
  "Version": "2012-10-17",
  "Statement": [
        {
        "Action": "execute-api:Invoke",
        "Effect": "Deny",
        "Resource": None
        }
    ]
  },
  "context": {}
}

class ReqAuthorizer(object):
    """
    """
    def __init__(self, event):
        try :
            self.token = event['headers']['Authorization']
            self.access_token = event['headers']['Access-Token']
            self.resource = event['methodArn']
            self.app_key = None
            self.param_err = False
        except Exception as err:
            print(f"Exception: {err}")
            self.param_err = True
        
    def validate(self):
        "Use Auth token for Authentication"
        try:
            # validate Bearer token 
            parts = self.token.split(' ')
            if parts[0] != 'Basic':
                print("Rejected: Invalid Authorization Header")
                return False
            key = parts[-1]
            self.app_key = key if type(key) is str else key.decode('utf8')    
        except Exception as err:
            # whatever, it aint good
            print(f"Validation Exception: {err}")
            return False
        
        # ok, token was valid
        return True

    def getProfile(self):
        """
        Attempt to retrieve client profile using
        token data
        """
        # get service connection
        ddb = boto3.resource('dynamodb')

        # query ddb
        tab = ddb.Table(DDB_TABLE)
        response = tab.get_item(
            Key={
                "api_key": self.app_key,
            }
        )

        return response['Item']

    def doAuth(self):
        """
        Make call into DDB using the key/secret
        to access the customer profile and set
        up user / store # data after authorizing
        endpoint
        """
        # approve access
        prof = None
        try: 
            # get targeted endpoint
            parts = self.resource.split("/")
            verb = parts[2]
            endpt = f"/{'/'.join(parts[3:])}"

            # get permited endpoints
            prof = self.getProfile()
            
            # validate access token against profile token
            if self.access_token not in prof['access_tokens']:
                raise Exception("Invalid Access Token")
            for tst in prof['api_permits'][verb]:
                prof['access_token'] = self.access_token
                # and test for first match
                if tst == endpt:
                    AWSPolicy['policyDocument']['Statement'][0]['Effect'] = 'Allow'
                    break
            # lose the key before sending along    
            del(prof['api_key'])
        except Exception as err:
            prof = False
            print(f'Authentication Exception: {err}')

        # all done
        return prof

    def run(self):
        """
        Authenticate and Authorize
        """
        if self.param_err:
            # explicit deny 
            print("Invalid input parameters")
            AWSPolicy['policyDocument']['Statement'][0]['Effect'] = 'Deny'
        else:
            try: 
                if self.validate():
                    prof = self.doAuth()
                    if prof:
                        AWSPolicy["context"]["gwxid"] = prof["gwxid"]
                        AWSPolicy["context"]["gwxurl"] = prof["worx_url"]
                        AWSPolicy["context"]["access_token"] = prof["access_token"] 
            except:
                pass
    
        print(AWSPolicy)
        return  AWSPolicy

def handler(event, context):
    "Evaluate access request from outside"
    # prep policy statement
    AWSPolicy['policyDocument']['Statement'][0]["Resource"] = event['methodArn']
    
    # validate and auth check
    return  ReqAuthorizer(event).run()
