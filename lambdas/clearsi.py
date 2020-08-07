"""
CSI Alerts Report
"""
from datetime import datetime as DT, timedelta as TD
import dateutil.parser as DTP
import json
import logging
import os
import queue
import threading
import time
import uuid

# layers
import dbc
import sicommon as SIC

#set up logging
logger = logging.getLogger()
if os.environ["DEBUG"]:
    logger.setLevel(logging.INFO)
else:
    logger.setLevel(logging.ERROR)

SQL = {
    "getInstances": 
        """
        select t.name, i.localkey, i.rmtkey,i.appid, ai.description,
            ap.name || ds.pgname as dbid
        from dwxAccessToken a
        JOIN dwxMasterIndex i on  a.gwxid = i.localkey
        join dwxTierInstance t on i.localkey = t.dwxid
        join dwxAppInstance ai on i.appid = ai.rkey
        join dwxDatastore ds on ai.storeid = ds.rkey
        join dwxAppServer ap on ds.serverid = ap.rkey
        where a.access_token = %s and objid = 2
        """,
    "gatherServiceIssues":"Select distinct * from vwCSIWorkOrder",
    "markServiceIssues":
        """
        Update dwmWorkorder 
           Set runid = %s
         Where keyacct = %s
           and runid is null;
        """,
        
    "initRunId": "Insert into ssicsirunid(runid) values(%s);"
}

FALSIES = ['False','FALSE','false','Off','off','0', 0, False]

class ReportSection(threading.Thread):
    """
    Worker thread to collect current issues from 
    individual DSD instance.
    """
    def __init__(self, conf, que):
        """
        Setup to be a good thread
        """
        threading.Thread.__init__(self)
        self.conf = conf
        self.queue = que
        self.test = False

    def formatQuery(self, query):
        """
        User input adjustments to filter
        """
        filter = self.conf['filter']
        params = []

        if filter['woid']: 
            # overrides all others with specific slot request 
            query = f"{query} where woid = %s"
            params.append(filter['woid'])
            return query, params

        # else plod on through    
        for k in filter:
            if not filter[k]:
                continue
            val = filter[k]
            
            conj = ' and ' if len(params) else ' where '
            if k == 'from':
                query = f"{query}{conj}(stdate + sttime) >= %s"
                params.append(val)
            if k == 'to':
                query = f"{query}{conj}(stdate + sttime) < %s"
                params.append(val)
            if k == 'retailer':
                query = f"{query}{conj}rid = %s"
                params.append(val)
            if k == 'vendor':
                query = f"{query}{conj}vendid = %s"
                params.append(val)
            if k == 'store':
                query = f"{query}{conj} %s ~ sitename"
                params.append(val)
            if k == 'ready':
                if val:
                    query = f"{query}{conj}runid = %s"
                    params.append(self.conf['runid'])
            if k == 'test':
                self.test = True
        
        # always filter by key account
        query = f"{query} and keyacct = %s"
        params.append(self.conf['rec'][SIC.RKEY])

        return query, params

    def run(self):
        """
        Connect to remote db and pull workorders
        """
        # convenience
        fltr = self.conf['filter']
        rid = self.conf['runid']

        # Get db connector for dbid
        logger.info(f"Connecting to {self.conf['rec'][SIC.DBID]}")
        conn = dbc.DBC(self.conf['rec'][SIC.DBID]).connect()
        with conn.cursor() as crsr:
            # register run id if we are collecting
            # new alerts an
            if fltr['ready']:
                crsr.execute(SQL['initRunId'], (rid,))
                logger.info(f"Query: {crsr.query}")
            
                # claim Issues
                crsr.execute(SQL['markServiceIssues'], (rid, self.conf['rec'][SIC.RKEY]))
                logger.info(f"Query: {crsr.query}")

            # format query with filter from user param
            qry, params = self.formatQuery(SQL['gatherServiceIssues'])
            logger.info(f"{qry} -> {params}")

            # execute formatted query with params
            crsr.execute(qry, tuple(params))
            logger.info(f"Query: {crsr.query}")
            for rec in crsr:
                # format and queue item for return
                self.queue.put(SIC.format_item(self.conf, rec, rid))
        
        # and seal the deal if not test
        if self.test:
            conn.rollback()
        else:
            conn.commit()
        
        return 


class Collector(threading.Thread):
    """ 
    thread runner to collect up results
    of the various instance queries
    """
    def __init__(self, que, arr):
        """
        Setup to be a good thread
        """
        threading.Thread.__init__(self)
        self.data = arr
        self.queue = queue
        
    def run(self):
        logger.info("Collecting...")
    
        while True:
            self.data.append(self.queue.get())


class CSIReport(object):
    """
    Collect and return unreported service issues 
    from each of the DSD instances in the warehouse
    where entity is defined.
    """
    def __init__(self, gwxid, gwxwhs, access_token):
        """
        report is run by gwxid for access_token holders
        in any / all dsd system(s) connected to the 
        identified warehose.
        """
        self.gwxid = gwxid
        self.token = access_token
        self.home = gwxwhs
        self.queue = queue.SimpleQueue()
    
        # good result template
        self.json = { 
            "type": "alerts",
            "data": {
                "result_code": 200,
                "result_message": "Success",
                "alerts": []
            },
            "success": True
        }
    
    def collect(self):
        logger.info("Collecting...")
    
        while True:
            self.json['data']['alerts'].append(self.queue.get())

    def setFilter(self,params):
        """
        Build parameters into filter object
        """
        filter = {
            "keyacct": self.gwxid,
            "from": None,
            "to": None,
            "retailer": None,
            "vendor": None,
            "store": None,
            "woid": None,
            "ready": True,
            "test": False
        }
        for k in params:
            v = params[k]
            if k == 'from':
                filter["from"] = DTP.parse(v)
            elif k == 'to':
                filter["to"] = DTP.parse(v)
            elif k == 'retailer_id':
                filter['retailer'] = v
            elif k == 'store_no':
                filter['store'] = v
            elif k == 'vendor_no':
                filter['vendor'] = v
            elif k == 'id':
                filter['woid'] = v.split("-")[1]
            elif k == 'ready':
                filter['ready'] = v not in FALSIES
            elif k == 'test':
                filter['test'] = True

        # biz rules...
        if filter['to'] and not filter['from']:
            raise Exception("Parameter Error: 'to' requires 'from'")
        if filter['store'] and not filter['retailer']:
            raise Exception("Parameter Error: 'store_no' requires 'retailer_id'")
        if not filter['ready'] and not filter['from']:
            raise Exception("Parameter Error: 'ready=False' requires 'from'")
        
        logger.info(f"Filter: {filter}")
        return filter
        
    def run(self, params):
        """
        Trigger the report collection
        """
        if not params:
            params = {}
        filter = {}
        # try:
        # build parameters
        logger.info(f"qs: {params}")
        try:
            filter = self.setFilter(params)
        except Exception as err:
            return { 
                "type": "Alerts",
                "error": {
                    "result_code": 400,
                    "result_message": f"{err}",
                },
                "success": False
            }
        # except Exception as err:
        #    logger.error(f"Parameter Error: {err}")
        #    return {
        #                "type": "Alerts",
        #                "errors": [f"Parameter Error: {err}"],
        #                "success": False                
        #            }            
        # start up the collection engine
        threading.Thread(target=self.collect, daemon=True).start()

        # Get connection to central whse db
        conn = dbc.DBC(self.home).connect() 
        logger.info("Connected...")

        with conn.cursor() as crsr:
            # gather all dsd instances for the gwxid
            workers = []
            crsr.execute(SQL['getInstances'], (self.token,))
            for inst in crsr:
                logger.info(f"Getting {inst}")
                
                # enhance the query with local goodies
                conf = {
                    "filter": filter,
                    "runid": f'{uuid.uuid4()}',
                    "keyacct": self.gwxid,
                    "rec": inst
                }
            
                # build worker thread and start it up
                wkr = ReportSection(conf, self.queue)
                wkr.start()
                workers.append(wkr)

            # wait until everybody get done
            for wkr in workers:
                wkr.join()

            # and the queue is empty
            while not self.queue.empty():
                time.sleep(.02)

        # all done
        return self.json

        
def handler(event,context):
    # report params from authorizer
    ctx = event['requestContext']['authorizer']
    logger.info("Starting")
    
    # run report and return results
    rpt = CSIReport(ctx['gwxid'], ctx['gwxwhs'], ctx['access_token']).run(event['queryStringParameters'])
    logger.info(rpt)
    return {
        "isBase64Encoded": False,
        "statusCode": 200,
        "headers": { "Content-Type": "application/json"},
        "body": json.dumps(rpt)
    }
    
