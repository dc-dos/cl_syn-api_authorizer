"""
- Map incomming REST Call to a Worx Call, 
- Make the Worx call 
- Passthrough response
"""
import json
import urllib
from urllib.parse import parse_qs, urlencode

# log high verosity flag
DEBUG = True

GOOD_RESULTS = ['100','200', 100, 200]

VERB_TABLE = {
    "POST": "Create",
    "GET": "Fetch",
    "POST": "",
    "DELETE": "Delete"
}

class WorxProxy(object):
    """
    Worker class for REST => Worx Proxy
    """
    def __init__(self, event):
        self.event = event
        self.context = event['requestContext']['authorizer']

    def run(self):
        """
        parse input, make http call and return results
        """
        # start with base Worx url
        endpt = self.context["gwxurl"]
        access_token = self.context["access_token"]
        gwxid = self.context["gwxid"]
        hdrs = self.event['headers']
        print(hdrs)
        
        # infer the action from method
        # and path nodes. (REST => Worx)
        method = self.event['httpMethod']
        verb = path = None
        if method == "PUT":
            verb = path.pop().capitalize()
        else: 
            verb = VERB_TABLE[method]
            path = self.event['path'].split("/")[1:]
        
        # build out Worx Action
        action = f'{".".join(path)}.{verb}'
        
        # start the process of getting the body set up
        body = {}
        data = None

        if method == 'PATCH':
            # preserve patch body and query string
            params = urlencode(self.event['queryStringParameters'])
            endpt = f'{endpt}?action={action}&{params}'
            hdrs['Content-Type'] = 'application/json'
            data = json.dumps(self.event['body']).encode('utf8') 
        else:
            # load up params in body
            # check for formdata, json and jsonstring 
            if self.event['body']:
                params = {}
                try:
                    params = parse_qs(self.event['body'])
                except:
                    pass

                if params:
                    body = {k:v[0] for k,v in params.items()} 
                else:
                    body = self.event['body']
                    if type(body) is str:
                        body = json.loads(body)

                    # if json.api, need to flatten
                    if 'type' in body and 'data' in body:
                        data = body['data']
                        del(body['data'])
                        body.update(data)
                            

                # add query string to body data 
                # (ok for for Worx)
                if self.event['queryStringParameters']:
                    body.update(self.event['queryStringParameters'])
            
            # add in extras from profile etc.
            body['gwxid'] = gwxid
            body['action'] = action

            # GET and DELETE use queryString, others use form
            if method in ('GET','DELETE'):
                
                endpt = f'{endpt}?action={action}&{urlencode(body) }'
                data = None
            else:
                # add form content header to POST, PUT
                # and format data as urlencoded form
                data = urlencode(body).encode("utf8")
                hdrs['Content-Type'] = 'application/x-www-form-urlencoded'
        # now that we have all input data collected, 
        # validate access token against profile token
        if access_token != body['access_token']:
            print("Error: Invalid Access Token!")
            res = { "result_code": 500, "result_message": f"Exception: {err}", "result_body": ''}
        else:
            # run the proxy to worx
            if DEBUG:
                print(f"Calling {method} on {endpt} with payload:")
                print(data)
                print("Headers:")
                print(hdrs)
    
            # fire http ball and
            req = urllib.request.Request(
                url=endpt,
                headers=hdrs, 
                method=method, 
                data=data
                )
            res = None
            try:
                res = {}
                with urllib.request.urlopen(req) as conn:
                    
                    rbody = json.loads()
                    res['result_body'] =  rbody if rbody and json.dumps(rbody) else None,
                    res['result_code'] = f.status
                    res['result_message'] = f.reason if GOOD_RESULTS.index(f.status) < 0 else 'Success'

                    if DEBUG:
                        print("Results:")
                        print(res)
            except Exception as err:
                print(f"Exception: {err}")
                res = { "result_code": 500, "result_message": f"Exception: {err}", "result_body": ''}

        # done
        return  {
                    "isBase64Encoded": False,
                    "statusCode": res['result_code'],
                    "body": self.apiResponse(res['result_body']),
                    "headers": {
                        "Content-Type": "application/json"
                    }
                }

    def apiResponse(self, typ, res):
        """
        Format simple JSON.API style response
        """
        rsp = {
            "type": typ
        }
        if res['result_code'] == 200:
            data = res['result_body']
            rsp['success'] = True
            rsp['data'] = json.loads(data) if data else ''
        else:
            rsp['success'] = False;
            rsp['error'] = res['result_message']   

        return json.dumps(rsp)

# handler
def handler(event, context):
    return WorxProxy(event).run()
