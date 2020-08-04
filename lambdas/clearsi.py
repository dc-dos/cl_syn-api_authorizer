
import dateutil.parser as DTP
import json
import logging
import os
import queue
import threading

import dbc
import sicommon as SIC

# SQL Statements
SQL = {
    "getInstance": 
        """
        select t.name, i.rmtkey as mfg, i.rmtkey, i.appid, ai.description,
              ap.name || ds.pgname as dbid
          from dwxMasterIndex i
          join dwxTierInstance t on i.localkey = t.dwxid
          join dwxAppInstance ai on i.appid = ai.rkey
          join dwxDatastore ds on ai.storeid = ds.rkey
          join dwxAppServer ap on ds.serverid = ap.rkey
         where i.localkey=%s and i.objid=2 and i.appid=%s
         """, 
    "getInstances": 
        """
        select t.name, i.rmtkey as mfg, i.appid, ai.description,
              ap.name || ds.pgname as dbid
          from dwxMasterIndex i
          join dwxTierInstance t on i.localkey = t.dwxid
          join dwxAppInstance ai on i.appid = ai.rkey
          join dwxDatastore ds on ai.storeid = ds.rkey
          join dwxAppServer ap on ds.serverid = ap.rkey
         where i.localkey=%s and i.objid=2;
        """,
    "find": 
        """
        select distinct * 
          from vwCSIWorkorder 
          where woid = %s
        """,
    "clear": "update dwmWorkorder set runid = null where sched = %s",
    "check": "Select rollbackdts from ssicsirunid where runid = %s",
    "rollback": "Update dwmWorkorder set runid = null where runid = %s",
    "updateRunid": "update ssicsirunid set rollbackdts=now() where runid = %s"            
}

#set up logging
logger = logging.getLogger()
if os.environ["DEBUG"]:
    logger.setLevel(logging.INFO)
else:
    logger.setLevel(logging.ERROR)


class Rollback(threading.Thread):
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
        self.test = False if "test" not in conf else conf['test']

    def run(self):
        """
        Connect to remote db and execute rollback
        """
        # convenience
        rid = self.conf['runid']
        err = err_msg = rslt_msg = None

        # Get db connector for dbid
        conn = dbc.DBC(self.conf['rec'][DBID]).connect()
        with conn.cursor() as crsr:
            crsr.execute(SQL['check'], (rid,))
            logger.info(f"query: {crsr.query}")

            row = crsr.fetchone()
            if row == None:
                err = 400
                rslt_msg = "Not Found"
                err_msg = f"Batch with RunID: {rid} not found"
            else:
                if row[0]:
                    err = 500
                    err_msg = f"Batch {rid} was previously rolled back on {row[0]}"
                    rslt_msg = "Duplicate"

                         
            if not err:
                # register run id 
                crsr.execute(SQL['rollback'], (rid,))
                logger.info(f"Query: {crsr.query}")

            if err:
                # error return
                self.queue.put({ 
                    "type": "Rollback",
                    "runid": rid,
                    "error": {
                        "result_code": err,
                        "result_message": rslt_msg,
                    },
                    "success": False
                })

        # check test flag before committing
        if not self.test:
            conn.commit()

        # good return
        self.queue.put({ 
            "type": "Rollback",
            "data": {
                "result_code": 200,
                "result_message": "Success",
                "alerts": {
                    "runid": rid
                }
            },
            "success": True
        })


class ClearSI(object):
    """
    Collect and return unreported service issues 
    from each of the DSD instances in the warehouse
    where entity is defined.
    """
    def __init__(self, gwxid, gwxwhs, params):
        """
        report is run by gwxid for access_token holders
        in any / all dsd system(s) connected to the 
        identified warehose.
        """
        self.gwxid = gwxid
        self.home = gwxwhs
        self.params = params
        self.test = "test" in params

    def clear(self, inst, woid):
        """
        Find workorder in instance and clear runid
        mmddyyyyhhmmss
        """
        itm = None
        
        conn = dbc.DBC(inst[SIC.DBID]).connect()
        logger.info(f"Connected to {inst[SIC.DBID]}...")
        try:
            with conn.cursor() as crsr:
                # verify 
                crsr.execute(SQL['find'], (woid, ))
                logger.info(f"{crsr.query}")

                rec = crsr.fetchone() 
                if rec:
                    if not rec[SIC.IRUNID]:
                        raise Exception(f"Slot already clear")
                    # clear the slot
                    crsr.execute(SQL['clear'], (woid,))
                    logger.info(f"{crsr.query}")

                    itm = { 
                        "type": "Reset",
                        "data": {
                            "result_code": 200,
                            "result_message": "Success",
                            "alerts": {
        
                            },
                        },
                        "success": True
                    }

                if not self.test:
                    conn.commit()
        except Exception as err:
            logger.error(f"Reset Error: {err}")

            itm = { 
                "type": "Reset",
                "error": {
                    "result_code": 400,
                    "result_message": f"{err}"
                },
                "success": False
            }
        
        # not found check
        if not itm:
            itm = { 
                "type": "Reset",
                "error": {
                    "result_code": 404,
                    "result_message": "Not Found",
                },
                "success": False
            }
        return itm

    def run(self):
        """
        Trigger the collection rollback
        """
        itm = None

        # Get connection to central whse db
        conn = dbc.DBC(self.home).connect()

        if "slot_id" in self.params:
            slot = self.params['slot_id']
            sinfo = slot.split("-")
            woid = sinfo[1]
            appid = sinfo[0]

            # clearing specific slot...
            logger.info(f"Clearing slot {slot}")
                        
            with conn.cursor() as crsr:
                # gather all dsd instances for the gwxid
                crsr.execute(SQL['getInstance'], (self.gwxid,appid))
                inst = crsr.fetchone()
                itm = self.clear(inst, woid)
                if itm['success']:
                    itm['data']['alerts'] = {"id": slot}
                else:
                    itm["id"] = slot

        elif "runid" in self.params:
            rq = queue.Queue()
            with conn.cursor() as crsr:
                # gather all dsd instances for the gwxid
                workers = []
                crsr.execute(SQL['getInstances'], (self.gwxid,))
                logger.info(f"query: {crsr.query}")
                for inst in crsr:
                    logger.info(f"Getting {inst}")
                    
                    # enhance the query with local goodies
                    conf = {
                        "runid": self.runid,
                        "rec": inst
                    }

                    # build worker thread and start it up
                    wkr = Rollback(conf, rq)
                    wkr.start()
                    workers.append(wkr)

            # wait until everybody get done
            for wkr in workers:
                wkr.join()
            
            itm = rq.get()

        else:
            itm = { 
                "type": "Reset",
                "error": {
                    "result_code": 400,
                    "result_message": "Parameter Input Error",
                },
                "success": False
            }
        # all done
        return itm
        
def handler(event,context):
    # report params from authorizer
    logger.info(event)
    ctx = event['requestContext']['authorizer']
    
    # run report and return results
    rs = ClearSI(ctx['gwxid'], ctx['gwxwhs'], json.loads(event['body'])).run()
    
    return {
        "isBase64Encoded": False,
        "statusCode": 200 if not 'error' in rs else rs['error']['result_code'],
        "headers": { "Content-Type": "application/json"},
        "body": json.dumps(rs)
    }
