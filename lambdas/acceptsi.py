"""
- Map incomming REST Call to a Worx Call, 
- Make the Worx call 
- Passthrough response
"""
import json
import logging
import os
import urllib.request
from urllib.parse import parse_qs, urlencode

import dbc

# log high verosity flag
DEBUG = os.environ['DEBUG']

#set up logging
logger = logging.getLogger()
if DEBUG:
    logger.setLevel(logging.INFO)
else:
    logger.setLevel(logging.ERROR)

SQL = {
    "getInfo": 
        """
        select ai.appid as apptype, dap.name || ds.pgname as dbid
          from dwxAppInstance ai
          join dwxDatastore ds on ai.storeid = ds.rkey
          join dwxAppServer dap on ds.serverid = dap.rkey
         where ai.rkey = %s
        """,
    "getEmpid": "select ukey from dwmsidetail where woid = %s",
    "getNotes": "select notes from dwmslot where woid = %s and status != 96"
}

# HTTP GOOD
GOOD_RESULTS = ['100','200', 100, 200]

ACTIONS = {
    "accept": "schedule.AcceptIssue",
    "complete": "schedule.CheckOut"
}

class WorxProxy(object):
    """
    Worker class for REST => Worx Proxy
    """
    def __init__(self, event):
        """
        save incoming data and pull the authoriser addins out
        """
        self.event = event
        self.context = event['requestContext']['authorizer']

    def getAccess(self, id):
        """
        Build out worx access tag
        """
        prts = id.split("-")
        appid = prts[0]
        woid = prts[1]
        apptype = empid = dbid = None

        conn = dbc.DBC(self.context['gwxwhs']).connect()
        with conn.cursor() as crsr:
            crsr.execute(SQL['getInfo'], (appid, ))
            rec = crsr.fetchone()
            apptype = rec[0]
            dbid = rec[1]
        
        conn = dbc.DBC(dbid).connect()
        with conn.cursor() as crsr:
            crsr.execute(SQL['getEmpid'], (woid, ))
            rec = crsr.fetchone()
            empid = rec[0]
        
        # save for results....
        self.dsd = conn
        self.woid = woid

        return f"{appid}~{apptype}~{empid}"

    def getNotes(self):
        notes = None
        with self.dsd.cursor() as crsr:
            crsr.execute(SQL['getNotes'], (self.woid, ))
            rec = crsr.fetchone()
            notes = rec[0]

        return notes

    def setEndpoint(self):
        """
        set up for specific worx action
        """
        # start the process of getting the body set up
        body = json.loads(self.event['body'])
        self.slot = body['id']
        resource = self.event['resource'].split('/')[-1]
        params = {
            "action":  ACTIONS[resource],            
            "id": body['id'],
            "access": self.getAccess(body['id']),
        }

        if resource == 'accept':
            params["accptopt"] =  body['resolution']
            params["comments"] = body['notes']
        else:
             params["notes"] = body['notes']

        # build full url and return http info
        return {
            "endpoint": f"{self.context['gwxurl']}?{urlencode(params)}",
            "method": "GET",
            "body": None
        }
        
    def run(self):
        """
        make worx call and return results
        """
        # set up http stuff
        hdrs = {'Authorization': self.event['headers']['Authorization'], "Accept": "*/*"}
        content_type = self.event['headers']['Content-Type']
        
        httpCall = self.setEndpoint()
        
        # now that we have all input data collected, 
        # run the proxy to worx
        if DEBUG:
            print(f"Calling: {httpCall['endpoint']}:")
            print(f"Body: {httpCall['body']}")
            print(f"Headers: {hdrs}")

        # fire http ball and
        req = urllib.request.Request(httpCall['endpoint'], httpCall['body'], headers=hdrs, method=httpCall['method'])
        res = {}
        try:
            with urllib.request.urlopen(req) as conn:
                # process the results 
                the_page = conn.read()
                res['result_code'] = conn.status
                res['result_message'] = conn.reason if GOOD_RESULTS.index(conn.status) < 0 else 'Success'

                if DEBUG:
                    print("Results:")
                    print(res)

        except Exception as err:
            print(f"Exception: {err}")
            res = { "result_code": 500, "result_message": f"Exception: {err}", "result_body": ''}

        

        # done
        return  self.apiResponse({ 
                    "result_code": 200,
                    "result_message": "success",
                    "alert": {
                        "id": self.slot,
                        "notes": self.getNotes()
                    }
                })

    def apiResponse(self, res):
        """
        Format simple JSON.API style response
        """
        rsp = {
            "type": "Service Issue",
        }
 
        if res['result_code'] in  [100, 200]:
            rsp['data'] = res
            rsp['success'] = True
        else:
            rsp['success'] = False;
            rsp['errors'] = [res['result_message']]   
            
        return rsp


# handler
def handler(event, context):
    logger.info(event)
    rv = WorxProxy(event).run()
    resp = {
        "isBase64Encoded": False,
        "statusCode": rv['data']['result_code'],
        "headers": { "Content-Type": "application/json"},
        "body": json.dumps(rv)
    }
    
    return resp
