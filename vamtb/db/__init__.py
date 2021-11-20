'''Vam dir structure'''
import sqlite3
from vamtb.file import FileName
from tqdm import tqdm
from vamtb.varfile import Var, VarFile
from vamtb import vamex
import zlib
from vamtb.utils import *
from vamtb.log import *

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

    def __init__(self, dbfilename="vars.db"):
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
            SIZE    INT     NOT NULL,
            CKSUM   CHAR(4) NOT NULL);''')

        self.getConn().execute('''CREATE TABLE IF NOT EXISTS DEPS
            (ID INTEGER PRIMARY KEY AUTOINCREMENT,
            VAR TEXT NOT NULL,
            DEPVAR TEXT NOT NULL,
            DEPFILE TEXT NOT NULL);''')

        self.getConn().execute('''CREATE TABLE IF NOT EXISTS FILES
            (ID INTEGER PRIMARY KEY AUTOINCREMENT,
            FILENAME TEXT NOT NULL,
            ISREF TEXT NOT NULL,
            VARNAME TEXT NOT NULL,
            SIZE    INT     NOT NULL,
            CKSUM   CHAR(4) NOT NULL);''')

    def fetchall(self, sql, row):
        """
        Execute query and fetch all results
        """
        cur = self.getConn().cursor()
        debug(f"Params={row}, Exec={sql}")
        if row:
            cur.execute(sql, row)
        else:
            cur.execute(sql)
        return cur.fetchall()

    def store_var(self, varfile):
        """ Insert (if NE) or update (if Time>) or do nothing (if Time=) """
        try:
            with Var(varfile) as var:
                sql = "SELECT * FROM VARS WHERE VARNAME=?"
                row = (var.var, )
                rows = self.fetchall(sql, row)
                if not rows:
                    creator, version, modified_time, cksum = (var.creator, var.version, var.mtime, var.crc)
                    size = FileName(var.path).size
                    v_isref="YES" if creator in ref_creators else "UNKNOWN"

                    meta = var.meta()
                    license=meta['licenseType']

                    cur = self.getConn().cursor()
                    sql = """INSERT INTO VARS(VARNAME,ISREF,CREATOR,VERSION,LICENSE,MODIFICATION_TIME,SIZE,CKSUM) VALUES (?,?,?,?,?,?,?,?)"""
                    row = (var.var, v_isref, creator, version, license, modified_time, size, cksum)
                    cur.execute(sql, row)

                    for f in var.files(with_meta=True):
                        crcf = f.crc
                        sizef = f.size
                        f_isref="YES" if creator in ref_creators else "UNKNOWN"

                        cur = self.getConn().cursor()
                        sql = """INSERT INTO FILES (ID,FILENAME,ISREF,VARNAME,SIZE,CKSUM) VALUES (?,?,?,?,?,?)"""
                        row = (None, var.ziprel(f.path), f_isref, var.var, sizef, crcf)
                        cur.execute(sql, row)

                    debug(f"Stored var {var.var} and files in databases")
                    sql = """INSERT INTO DEPS(ID,VAR,DEPVAR,DEPFILE) VALUES (?,?,?,?)"""
                    for dep in var.dep_fromfiles(with_file=True):
                        depvar, depfile = dep.split(':')
                        # Remove first /
                        depfile = depfile[1:]
                        row = (None, var.var, depvar, depfile)
                        cur = self.getConn().cursor()
                        cur.execute(sql, row)
                else:
                    assert( len(rows) == 1 )
                    db_varname, db_isref, db_creator, db_version, db_license, db_modtime, db_size, db_cksum = rows[0]
                    modified_time = FileName(var.path).mtime
                    
                    if db_modtime < modified_time and db_cksum != FileName(var.path).crc:
                        error(f"Database contains older data for var {var.var}. Not updating. Erase database file (or simply rows manually) and rerun vamtb dbs")
                        error(f"This could also be because you have duplicate vars for {var.var} (in that case, use vamtb sortvar) ")
                        return False
                    else:
                        debug(f"Var {var.var} already in database")
        except (zlib.error, vamex.VarExtNotCorrect, vamex.VarMetaJson, vamex.VarVersionNotCorrect, vamex.VarNameNotCorrect) as e:
            #error(f"Var {var} generated error {e}")
            return False
        return True

    def store_vars(self, vars_list, sync = True):
        progress_iterator = tqdm(vars_list, desc="Writing database…", ascii=True, maxinterval=5, ncols=75, unit='var')
        for varfile in progress_iterator:
            debug(f"Checking var {varfile}")
            if not self.store_var(varfile):
                self.getConn().rollback()
            elif sync:
                self.getConn().commit()
        info(f"{len(vars_list)} var files stored")

        self.getConn().commit()

    def get_prop_vars(self, varname, prop_name):

        sql = f"SELECT {prop_name} FROM VARS WHERE VARNAME=?"
        row = (varname,)
        res = self.fetchall(sql, row)
        if res:
            return res[0][0]
        else:
            return None

    def get_prop_files(self, filename, varname, prop_name):
        if varname.endswith(".var"):
            assert(False)
            varname = varname[0:-4]
        sql = f"SELECT {prop_name} FROM FILES WHERE FILENAME=? AND VARNAME=?"
        row = (filename, varname)
        res = self.fetchall(sql, row)
        if res:
            return res[0][0]
        else:
            return None

    def get_dep(self, varname):
        if varname.endswith(".var"):
            assert(False)
            varname = varname[0:-4]
        sql = f"SELECT DISTINCT DEPVAR FROM DEPS WHERE VAR=?"
        row = (varname,)
        res = self.fetchall(sql, row)
        res = [ e[0] for e in res]
        return res if res else []

    def get_file_cksum(self, filename, varname):
        return self.get_prop_files(filename, varname, "CKSUM")

    def get_license(self, varname):
        if varname.endswith(".var"):
            assert(False)
            varname = varname[0:-4]
        return self.get_prop_vars(varname, "LICENSE")

    def get_var_size(self, varname):
        return self.get_prop_vars(varname, "SIZE")

    def get_ref(self, varname):
        return self.get_prop_vars(varname, "ISREF")

    def var_exists(self, varname):
        if varname.endswith(".var"):
            assert(False)
            varname = varname[0:-4]
        if varname.endswith(".latest"):
            return (self.latest(varname) != None)
        else:
            return (self.get_prop_vars(varname, "VARNAME") != None)

    def latest(self, var):
        sql="SELECT VARNAME FROM VARS WHERE VARNAME LIKE ? COLLATE NOCASE"
        var_nov = VarFile(var).var_nov
        row=(f"{var_nov}%", )
        res = self.fetchall(sql, row)
        versions = [ e[0].split('.',3)[2] for e in res ]
        versions.sort(key=int, reverse=True)

        if versions:
            return f"{var_nov}.{versions[0]}"
        else:
            return None

    def min(self, var):
        varf = VarFile(var)
        assert(varf.version.startswith("min"))
        minver = varf.minversion
        sql="SELECT VARNAME FROM VARS WHERE VARNAME LIKE ? COLLATE NOCASE"
        var_nov = varf.var_nov
        row=(f"{var_nov}%", )
        res = self.fetchall(sql, row)
        versions = [ e[0].split('.',3)[2] for e in res ]
        versions = [ int(v) for v in versions if int(v) >= minver ]
        versions.sort(key=int, reverse=True)

        if versions:
            return f"{var_nov}.{versions[0]}"
        else:
            return None

    def get_db_deps(self):
        return self.fetchall("SELECT DISTINCT VAR, DEPVAR FROM DEPS", None)

def store_vars(var_files):
    dbs = Dbs()
    dbs.store_vars(vars_list=var_files)