import json
import dbc

def handler(event,context):
    db = dbc.DBC('csigwx1')
    conn = db.connect()
    
    return json.dumps('{"Code": 200, "Msg":" "OK"}')