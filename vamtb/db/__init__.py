'''Vam dir structure'''
import os
import logging
import sqlite3
from tqdm import tqdm
from pathlib import Path
from vamtb import varfile
from vamtb import vamex
import subprocess
from zipfile import ZipFile


ref_creators = (
"50shades", "AcidBubbles", "AmineKunai", "AnythingFashionVR","AshAuryn",
"bvctr", "CosmicFTW","Errarr","GabiRX","geesp0t","hazmhox","Hunting-Succubus",
"Jackaroo","JoyBoy","kemenate", "LFE","MacGruber","MeshedVR","Miki","Molmark","NoStage3","Oeshii",
"Roac","SupaRioAmateur", "TenStrip", "TGC", "VL_13")


class Dbs:
    __instance = None
    __conn = None

    @staticmethod 
    def getInstance():
        """ Static access method. """
        if Dbs.__instance == None:
            Dbs()
        return Dbs.__instance

    @staticmethod 
    def getConn():
        """ Static access method. """
        return Dbs.__conn

    def __init__(self, dbfilename="vars.dbs"):
        """ Virtually private constructor. """
        if Dbs.__instance != None:
            raise Exception("This class is a singleton!")
        else:
            Dbs.__conn = sqlite3.connect(dbfilename)
            self.init_dbs()
            Dbs.__instance = self

    def init_dbs(self):
        """
        Create table if not exist
        """
        self.getConn().execute('''CREATE TABLE IF NOT EXISTS VARS
            (VARNAME TEXT PRIMARY KEY     NOT NULL,
            ISREF TEXT NOT NULL,
            CREATOR TEXT NOT NULL,
            VERSION INT NOT NULL,
            LICENSE TEXT NOT NULL,
            MODIFICATION_TIME    INT     NOT NULL,
            CKSUM   CHAR(4) NOT NULL);''')

        self.getConn().execute('''CREATE TABLE IF NOT EXISTS DEPS
            (ID INTEGER PRIMARY KEY AUTOINCREMENT,
            VAR TEXT NOT NULL,
            DEP TEXT NOT NULL);''')

        self.getConn().execute('''CREATE TABLE IF NOT EXISTS FILES
            (ID INTEGER PRIMARY KEY AUTOINCREMENT,
            FILENAME TEXT NOT NULL,
            ISREF TEXT NOT NULL,
            VARNAME TEXT NOT NULL,
            CKSUM   CHAR(4) NOT NULL);''')

    def fetchall(self, sql, row):
        """
        Execute query and fetch all results
        """
        cur = self.getConn().cursor()
        if row:
            cur.execute(sql, row)
        else:
            cur.execute(sql)
        return cur.fetchall()

    def store_var(self, var):
        """ Insert (if NE) or update (if Time>) or do nothing (if Time=) """
        varname = var.name

        sql = "SELECT * FROM VARS WHERE VARNAME=?"
        row = (varname, )
        rows = self.fetchall(sql, row)
        if not rows:
            creator, version, modified_time,cksum = varfile.get_props(var)
            v_isref="YES" if creator in ref_creators else "UNKNOWN"

            meta=varfile.extract_meta_var(var)
            license=meta['licenseType']

            cur = self.getConn().cursor()
            sql = """INSERT INTO VARS(VARNAME,ISREF,CREATOR,VERSION,LICENSE,MODIFICATION_TIME,CKSUM) VALUES (?,?,?,?,?,?,?)"""
            row = (varname, v_isref, creator, version, license, modified_time, cksum)
            cur.execute(sql, row)

            with ZipFile(var, mode='r') as myvar:
                listOfFileNames = myvar.namelist()
                for f in listOfFileNames:
                    with myvar.open(f) as fh:
                        try:
                            crcf = varfile.crc32c(fh.read())
                        except Exception as e:
                            logging.error(f'{Path(var).name} is a broken zip, chouldnt decompress {f}')
                            return False
                    f_isref="YES" if creator in ref_creators else "UNKNOWN"

                    cur = self.getConn().cursor()
                    sql = """INSERT INTO FILES (ID,FILENAME,ISREF,VARNAME,CKSUM) VALUES (?,?,?,?,?)"""
                    row = (None, f, f_isref, varname, crcf)
                    cur.execute(sql, row)

            logging.debug(f"Stored var {varname} and files in databases")
            sql = """INSERT INTO DEPS(ID,VAR,DEP) VALUES (?,?,?)"""
            for dep in varfile.dep_fromvar(dir=None, var=var, full=True):
                row = (None, varname[0:-4], dep)
                cur = self.getConn().cursor()
                cur.execute(sql, row)
        else:
            assert( len(rows) == 1 )
            db_varname, db_isref, db_creator, db_version, db_license, db_modtime, db_cksum = rows[0]
            modified_time = os.path.getmtime(var)
            if db_modtime < modified_time and db_cksum != varfile.crc32(var):
                logging.error(f"Database contains older data for var {varname}. Not updating. Erase database file (or simply rows manually) and rerun vamtb dbs")
                logging.error(f"This could also be because you have duplicate vars for {varname} (in that case, use vamtb sortvar) ")
                return False
            else:
                logging.debug(f"Var {varname} already in database")
        return True

    def store_vars(self, vars_list, sync = True):
        progress_iterator = tqdm(vars_list, desc="Writing database…", ascii=True, maxinterval=5, ncols=75, unit='var')
        for var in progress_iterator:
            logging.debug(f"Checking var {var}")
            if not self.store_var(var):
                self.getConn().rollback()
            elif sync:
                self.getConn().commit()
        logging.info(f"{len(vars_list)} var files stored")

        self.getConn().commit()

    def get_prop_vars(self, varname, prop_name):

        cur = self.getConn().cursor()
        sql = f"SELECT {prop_name} FROM VARS WHERE VARNAME=?"
        row = (varname,)
        cur.execute(sql, row)

        res = cur.fetchall()
        if res:
            return res[0][0]
        else:
            return None

    def get_prop_files(self, filename, varname, prop_name):
        cur = self.getConn().cursor()
        sql = f"SELECT {prop_name} FROM FILES WHERE FILENAME=? AND VARNAME=?"
        row = (filename, varname)
        cur.execute(sql, row)

        res = cur.fetchall()
        if res:
            return res[0][0]
        else:
            return None

    def get_file_cksum(self, filename, varname):
        return self.get_prop_files(filename, varname, "CKSUM")

    def get_license(self, varname):
        if not varname.endswith(".var"):
            varname = f"{varname}.var"
        return self.get_prop_vars(varname, "LICENSE")

    def get_ref(self, varname):
        return self.get_prop_vars(varname, "ISREF")

    def var_exists(self, varname):
        if not varname.endswith(".var"):
            varname = f"{varname}.var"
        if varname.endswith(".latest"):
            return (self.latest(varname) != None)
        else:
            return (self.get_prop_vars(varname, "VARNAME") != None)

    def latest(self, var):
        var = ".".join(var.split('.',2)[0:2])

        sql="SELECT VARNAME FROM VARS WHERE VARNAME LIKE ? COLLATE NOCASE"
        row=(f"{var}%", )
        res = self.fetchall(sql, row)
        versions = [ e[0].split('.',3)[2] for e in res ]
        versions.sort(key=int, reverse=True)

        if versions:
            return f"{var}.{versions[0]}"
        else:
            return None

    def get_db_deps(self):
        return self.fetchall("SELECT VAR, DEP FROM DEPS", None)

def store_vars(var_files):
    dbs = Dbs()
    dbs.store_vars(vars_list=var_files)