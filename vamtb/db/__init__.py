'''Vam dir structure'''
import sqlite3
from pprint import pprint

from vamtb.vamex import *
from vamtb.utils import *
from vamtb.log import *

# At import, modify our variables
global C_DB
global exec_dir

class Dbs:
    __instance = None
    __conn = None

    def __init__(self, dbfilename=C_DB):
        """
            This is a singleton (see at end) getting called quite early at import time
            Before any main code is executed.
        """
        if not Dbs.__instance:
            debug(f"Opened database {dbfilename}")
            Dbs.__conn = sqlite3.connect(dbfilename)
            Dbs.init_dbs()
            Dbs.__instance = self

    @staticmethod 
    def getConn():
        return Dbs.__conn

    @staticmethod
    def init_dbs():
        """
        Create table if not exist
        """
        Dbs.getConn().execute('''CREATE TABLE IF NOT EXISTS VARS
            (VARNAME TEXT PRIMARY KEY     NOT NULL,
            ISREF                TEXT NOT NULL,
            CREATOR              TEXT NOT NULL,
            VERSION              INT NOT NULL,
            LICENSE              TEXT NOT NULL,
            MODIFICATION_TIME    INT     NOT NULL,
            SIZE                 INT     NOT NULL,
            CKSUM                CHAR(4) NOT NULL);''')

        Dbs.getConn().execute('''CREATE TABLE IF NOT EXISTS DEPS
            (ID INTEGER PRIMARY KEY AUTOINCREMENT,
            VAR     TEXT NOT NULL,
            DEPVAR  TEXT NOT NULL,
            DEPFILE TEXT NOT NULL);''')

        Dbs.getConn().execute('''CREATE TABLE IF NOT EXISTS FILES
            (ID INTEGER PRIMARY KEY AUTOINCREMENT,
            FILENAME TEXT NOT NULL,
            ISREF    TEXT NOT NULL,
            VARNAME  TEXT NOT NULL,
            SIZE     INT     NOT NULL,
            CKSUM    CHAR(4) NOT NULL);''')

        Dbs.getConn().execute('''CREATE TABLE IF NOT EXISTS UPLOAD
         (VARNAME TEXT PRIMARY KEY     NOT NULL,
         IA TEXT NOT NULL,
         ANON TEXT NOT NULL);''')

    @staticmethod
    def fetchall(sql, row):
        """
        Execute query and fetch all results
        """
        cur = Dbs.getConn().cursor()
        # debug(f"Fetchall({sql}, {row})")
        if row:
            cur.execute(sql, row)
        else:
            cur.execute(sql)
        res = cur.fetchall()
        # debug(f"Fetchall={res}")
        return res

    @staticmethod
    def execute(sql, row):
        """ 
        Execute query and don't return anything
        """
        cur = Dbs.getConn().cursor()
        cur.execute(sql, row)

    @staticmethod
    def get_db_deps():
        return Dbs.fetchall("SELECT DISTINCT VAR, DEPVAR FROM DEPS", None)

    @staticmethod
    def get_vars():
        return [ e[0] for e in Dbs.fetchall("SELECT VARNAME FROM VARS", None) ]

    @staticmethod
    def update_values(table, d_sel: dict, d_col: dict):
        """
        update_value("TABLE", {"VARNAME": "foo.bar.1"}, {"COL1": "newvalue", "COL2": "newvalue"})
        """
        set_clause = " ".join(f"SET {key}='{value}'" for key, value in d_col.items())
        # TODO escape values
        where_clause = " AND ".join(f"{key}='{value}'" for key, value in d_sel.items())
        sql = f"UPDATE {table} {set_clause} WHERE {where_clause}"
        Dbs.execute(sql, ())

# Singleton as Global variable 
# FIXME make it testable
__dbs = Dbs()
