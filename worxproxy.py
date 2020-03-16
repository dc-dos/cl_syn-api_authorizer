"""
- Map incomming REST Call to a Worx Call, 
- Make the Worx call 
- Passthrough response
"""
import json
import urllib
from urllib.parse import parse_qs

# log high verosity flag
DEBUG = False

BASE_URL = "http://test3.rlsworx.com/Mobility/go.mbl"

GOOD_RESULTS = ['100','200', 100, 200]

VERB_TABLE = {
    "POST": "Create",
    "GET": "Create"
}

class WorxProxy(object):
    """
    Worker class for REST => Worx Proxy
    """
    def __init__(self, event, context):
        self.event = event
        self.context = context

    def run(self):
        """
        parse input, make http call and return results
        """
        # start with base Worx url
        endpt = f'{BASE_URL}'

        # infer the action from method
        # and path nodes. (REST => Worx)
        method = self.event['httpMethod']
        verb = VERB_TABLE[method]
        path = self.event['path'].split("/")[1:]
        action = f'{".".join(path)}.{verb}'
        body = {}
        # load up params in body
        if self.event['body']:
            params = parse_qs(self.event['body'])
            body = {k:v[0] for k,v in params.items()} 
        if self.event['queryStringParameters']:
            body.update(self.event['queryStringParameters'])
        body['action'] = action

        if method == 'GET':
            endpt = f'{endpt}?{urllib.encode(body)}'
            body = None
        if DEBUG:
            print(f"Calling {method} on {endpt} with payload:")
            print(body)

        # fire http ball and
        req = urllib.request.Request(url=endpt, method=method, data=urllib.parse.urlencode(body).encode("utf8"))
        res = None
        try:
            with urllib.request.urlopen(req) as f:
                res = json.loads(f.read())
                res['result_code'] = f.status
                res['result_message'] = f.reason if GOOD_RESULTS.index(f.status) < 0 else 'Success'
                    
                if DEBUG:
                    print("Results:")
                    print(res)
        except Exception as err:
            print(f"Exception: {err}")
            res = { "result_code": 500, "result_message": f"Exception: {err}"}
        return  {
                    "isBase64Encoded": False,
                    "statusCode": res['result_code'],
                    "body": json.dumps(res),
                    "headers": {
                        "Content-Type": "application/json"
                    }
                }

# handler
def handler(event, context):
    return WorxProxy(event, context).run()

if __name__ == '__main__':
    with open("req.json") as f:
        req = json.load(f)
    print(handler(req, {}))