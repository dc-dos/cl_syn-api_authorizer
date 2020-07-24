import os

import boto3
import psycopg2 as PG

DDB_TABLE = "cl_syn-db_configs"
APP_KEY = "csigwx1"

class DBC(object):
    def __init__(self, app_id):
        """
        Initialization
        """
        self.conn = None
        self.app_id = app_id
        self.conf = self.get_config()
    
    def get_config(self,app_id):
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
                "app_id": self.app_id,
            }
        )

        return response['Item']

    def connect(self):
        self.conn = self.conn if self.conn else PG.connect(**self.conf.db) 

        return self.conn
        
        
   