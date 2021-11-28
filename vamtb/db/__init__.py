'''Vam dir structure'''
import sqlite3
#from vamtb.ref import get_new_ref #FIXME move

from vamtb.vamex import *
from vamtb.utils import *
from vamtb.log import *

class Dbs:
    __instance = None
    __conn = None

    def __init__(self, dbfilename=C_DB):
        if not Dbs.__instance:
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

    @staticmethod
    def fetchall(sql, row):
        """
        Execute query and fetch all results
        """
        cur = Dbs.getConn().cursor()
        debug(f"Params={row}, Exec={sql}")
        if row:
            cur.execute(sql, row)
        else:
            cur.execute(sql)
        res = cur.fetchall()
        debug(f"Fetchall={res}")
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

# Singleton as Global variable 
__dbs = Dbs()
