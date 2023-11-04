import os
import psycopg2
import os
from typing import Any, Dict
import psycopg2
from typing import List
from datetime import datetime, timezone
from psycopg2.errors import UniqueViolation

DATABASE_URL = os.getenv("DATABASE_URL")

class Database:
    def __init__(self):
        self.conn = psycopg2.connect(DATABASE_URL,  sslmode='require')
        self.cursor = self.conn.cursor()
    
    def add_trade(self, asset, oid, direction):
        try:
            query = 'SELECT order_id FROM "trades" WHERE asset = %s'  # Use a placeholder for the asset value
            self.cursor.execute(query, (asset,))  # Pass asset as a parameter
            result = self.cursor.fetchone()
            
            if result:
                # If a record exists, update it
                update = 'UPDATE "trades" SET order_id = %s, direction = %s WHERE asset = %s'
                self.cursor.execute(update, (oid, direction, asset))  # Reversed the order of parameters
                self.conn.commit()
            else:
                # If no record exists, insert a new one
                query = 'INSERT INTO "trades" (asset, order_id, direction) VALUES (%s, %s, %s)'
                self.cursor.execute(query, (asset, oid, direction))
                self.conn.commit()
        except UniqueViolation as c:
            print("add asset", c)
            pass
        
    def get_order_id(self, asset):
        query = 'SELECT order_id FROM "trades" WHERE asset = %s'  # Use a placeholder for asset
        self.cursor.execute(query, (asset,))
        result = self.cursor.fetchone()
        if result:
            return result[0]
        else:
            return None
        
    def get_trades_by_asset(self, asset):
        query = 'SELECT * FROM "trades" WHERE asset = %s'
        self.cursor.execute(query, (asset,))
        results = self.cursor.fetchall()  # Fetch all matching rows
        return results
