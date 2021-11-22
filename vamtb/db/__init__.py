'''Vam dir structure'''
import sqlite3
from tqdm import tqdm
import zlib
from vamtb.varfile import Var, VarFile
from vamtb.file import FileName
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
    def store_var(varfile):
        """ Insert (if NE) or update (if Time>) or do nothing (if Time=) """
        try:
            with Var(varfile) as var:
                sql = "SELECT * FROM VARS WHERE VARNAME=?"
                row = (var.var, )
                rows = Dbs.fetchall(sql, row)
                if not rows:
                    creator, version, modified_time, cksum = (var.creator, var.version, var.mtime, var.crc)
                    size = FileName(var.path).size
                    v_isref="YES" if creator in C_REF_CREATORS else "UNKNOWN"

                    meta = var.meta()
                    license = meta['licenseType']

                    cur = Dbs.getConn().cursor()
                    sql = """INSERT INTO VARS(VARNAME,ISREF,CREATOR,VERSION,LICENSE,MODIFICATION_TIME,SIZE,CKSUM) VALUES (?,?,?,?,?,?,?,?)"""
                    row = (var.var, v_isref, creator, version, license, modified_time, size, cksum)
                    cur.execute(sql, row)

                    for f in var.files(with_meta=True):
                        crcf = f.crc
                        sizef = f.size
                        f_isref = "YES" if creator in C_REF_CREATORS else "UNKNOWN"

                        cur = Dbs.getConn().cursor()
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
                        cur = Dbs.getConn().cursor()
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
        except (zlib.error, VarExtNotCorrect, VarMetaJson, VarVersionNotCorrect, VarNameNotCorrect) as e:
            #error(f"Var {var} generated error {e}")
            return False
        return True

    @staticmethod
    def store_vars(vars_list, sync = True):
        progress_iterator = tqdm(vars_list, desc="Writing database…", ascii=True, maxinterval=5, ncols=75, unit='var')
        for varfile in progress_iterator:
            debug(f"Checking var {varfile}")
            if not Dbs.store_var(varfile):
                Dbs.getConn().rollback()
            elif sync:
                Dbs.getConn().commit()
        info(f"{len(vars_list)} var files stored")

        Dbs.getConn().commit()

    @staticmethod
    def get_prop_vars(varname, prop_name):

        sql = f"SELECT {prop_name} FROM VARS WHERE VARNAME=?"
        row = (varname,)
        res = Dbs.fetchall(sql, row)
        if res:
            return res[0][0]
        else:
            return None

    @staticmethod
    def get_prop_files(filename, varname, prop_name):
        sql = f"SELECT {prop_name} FROM FILES WHERE FILENAME=? AND VARNAME=?"
        row = (filename, varname)
        res = Dbs.fetchall(sql, row)
        if res:
            return res[0][0]
        else:
            return None

    @staticmethod
    def get_dep(varname):
        sql = f"SELECT DISTINCT DEPVAR FROM DEPS WHERE VAR=?"
        row = (varname,)
        res = Dbs.fetchall(sql, row)
        res = [ e[0] for e in res ]
        return res if res else []

    @staticmethod
    def get_file_cksum(filename, varname):
        return Dbs.get_prop_files(filename, varname, "CKSUM")

    @staticmethod
    def get_files(varname):
        sql = f"SELECT FILENAME FROM FILES WHERE VARNAME=?"
        row = (varname,)
        res = Dbs.fetchall(sql, row)
        if res:
            return [ e[0] for e in res ]
        else:
            return None

    @staticmethod
    def get_refvar_forfile(filename, varname):
        cksum = Dbs.get_file_cksum(filename, varname)
        sql = f"SELECT VARNAME, FILENAME FROM FILES WHERE CKSUM=? AND ISREF='YES' AND VARNAME!=? AND FILENAME LIKE ? GROUP BY VARNAME"
        row = (cksum,varname,f"%{Path(filename).name}")
        res = Dbs.fetchall(sql, row)
        if res:
            return res
        else:
            return None

    @staticmethod
    def get_license(varname):
        return Dbs.get_prop_vars(varname, "LICENSE")

    @staticmethod
    def get_var_size(varname):
        return Dbs.get_prop_vars(varname, "SIZE")

    @staticmethod
    def get_ref(varname):
        return Dbs.get_prop_vars(varname, "ISREF")

    @staticmethod
    def var_exists(varname):
        #TODO min
        if varname.endswith(".latest"):
            return (Dbs.latest(varname) != None)
        else:
            return (Dbs.get_prop_vars(varname, "VARNAME") != None)

    @staticmethod
    def latest(var):
        sql="SELECT VARNAME FROM VARS WHERE VARNAME LIKE ? COLLATE NOCASE"
        var_nov = VarFile(var).var_nov
        row = (f"{var_nov}%", )
        res = Dbs.fetchall(sql, row)
        versions = [ e[0].split('.',3)[2] for e in res ]
        versions.sort(key=int, reverse=True)

        if versions:
            return f"{var_nov}.{versions[0]}"
        else:
            return None

    @staticmethod
    def min(var):
        varf = VarFile(var)
        assert(varf.version.startswith("min"))
        minver = varf.minversion
        sql="SELECT VARNAME FROM VARS WHERE VARNAME LIKE ? COLLATE NOCASE"
        var_nov = varf.var_nov
        row = (f"{var_nov}%", )
        res = Dbs.fetchall(sql, row)
        versions = [ e[0].split('.',3)[2] for e in res ]
        versions = [ int(v) for v in versions if int(v) >= minver ]
        versions.sort(key=int, reverse=True)

        if versions:
            return f"{var_nov}.{versions[0]}"
        else:
            return None

    @staticmethod
    def get_db_deps():
        return Dbs.fetchall("SELECT DISTINCT VAR, DEPVAR FROM DEPS", None)

# Global var as singleton
__dbs = Dbs()