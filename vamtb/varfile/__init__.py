'''Var file naming'''
import json
import os
import re
import shutil
import tempfile
import json
from pprint import pp
from pathlib import Path
from zipfile import ZipFile

from vamtb.db import Dbs
from vamtb.file import FileName

from vamtb.vamex import *
from vamtb.utils import *
from vamtb.log import *

class VarFile:

    def __init__(self, inputName, use_db = False) -> None:
        inputName or critical("Tried to create a var but gave no filename", doexit=True)
        self.__Creator = ""
        self.__Resource = ""
        # Version as string 1, latest, min
        self.__sVersion = ""
        # integer version or 0
        self.__iVersion = 0
        # Min version or 0
        self.__iMinVer = 0
        # Db if a reference was provided
        self.__Dbs = Dbs if use_db else None

        if not isinstance(inputName, Path):
            inputName = Path(inputName)

        f_basename = inputName.name
        try:
            self.__Creator, self.__Resource, self.__sVersion = f_basename.split('.',3)[0:3]
        except ValueError:
            error(f"Var has incorrect format: {inputName}")
            raise VarNameNotCorrect(inputName)
        try:
            self.__iVersion = int(self.__sVersion)
        except ValueError:
            if self.__sVersion == "latest":
                pass
            elif self.__sVersion.startswith('min'):
                try:
                    self.__iMinVer = int(self.__sVersion[3:])
                except ValueError:
                    raise VarExtNotCorrect(inputName)
            else:
                error(f"Var has incorrect version: {inputName} version: {self.__sVersion}" )
                raise VarExtNotCorrect(inputName)
        try:
            _, _, _, ext = f_basename.split('.',4)
        except ValueError:
            pass
        else:
            if ext != "var":
                error(f"Var has incorrect extension: {inputName}" )
                raise VarExtNotCorrect(inputName)
        debug(f"Var {inputName} is compliant")

    @property
    def var(self) -> str:
        return f"{self.__Creator}.{self.__Resource}.{self.__sVersion}"

    @property
    def var_nov(self) -> str:
        return f"{self.__Creator}.{self.__Resource}"

    @property
    def file(self) -> str:
        return self.var + ".var"

    @property
    def creator(self) -> str:
        return self.__Creator

    @property
    def resource(self) -> str:
        return self.__Resource

    @property
    def version(self) -> str:
        return self.__sVersion

    @property
    def iversion(self) -> int:
        return self.__iVersion

    @property
    def minversion(self) -> int:
        return self.__iMinVer

    def db_exec(self, sql, row):
        if self.__Dbs:
            self.__Dbs.execute(sql, row)
        else:
            assert(False)

    def db_fetch(self, sql, row):
        if self.__Dbs:
            return self.__Dbs.fetchall(sql, row)
        else:
            assert(False)

    def db_commit(self, rollback = False):
        if self.__Dbs:
            if rollback:
                self.__Dbs.getConn().rollback()
            else:
                self.__Dbs.getConn().commit()
        else:
            assert(False)

    def store_var(self):
        """ Insert (if NE) or update (if Time>) or do nothing (if Time=) """
        creator, version, modified_time, cksum = (self.creator, self.version, self.mtime, self.crc)
        size = FileName(self.path).size
        v_isref="YES" if creator in C_REF_CREATORS else "UNKNOWN"

        meta = self.meta()
        license = meta['licenseType']

        sql = """INSERT INTO VARS(VARNAME,ISREF,CREATOR,VERSION,LICENSE,MODIFICATION_TIME,SIZE,CKSUM) VALUES (?,?,?,?,?,?,?,?)"""
        row = (self.var, v_isref, creator, version, license, modified_time, size, cksum)
        self.db_exec(sql, row)

        for f in self.files(with_meta=True):
            crcf = f.crc
            sizef = f.size
            f_isref = "YES" if creator in C_REF_CREATORS else "UNKNOWN"

            sql = """INSERT INTO FILES (ID,FILENAME,ISREF,VARNAME,SIZE,CKSUM) VALUES (?,?,?,?,?,?)"""
            row = (None, self.ziprel(f.path), f_isref, self.var, sizef, crcf)
            self.db_exec(sql, row)

        debug(f"Stored var {self.var} and files in databases")
        sql = """INSERT INTO DEPS(ID,VAR,DEPVAR,DEPFILE) VALUES (?,?,?,?)"""
        for dep in self.dep_fromfiles(with_file=True):
            depvar, depfile = dep.split(':')
            depfile = depfile.lstrip('/')
            row = (None, self.var, depvar, depfile)
            self.db_exec(sql, row)

        self.db_commit()
        return True

    def store_update(self, confirm = True):
        if self.exists():
            info(f"{self.var} already in database")
            if FileName(self.path).mtime == self.get_modtime or FileName(self.path).crc == self.get_cksum:
                return False
            info(f"Database is not inline.")
            if confirm == False:
                res = "Y"
            else:
                #TODO don't bug on bad char
                res = input(blue(f"Remove older DB for {self.path} [Y]N  ?"))
            if not res or res == "Y":
                self.db_delete() 
                self.db_commit()
            else:
                self.db_commit(rollback = True)
                return False
        return self.store_var()

    def exists(self):
        if self.var.endswith(".latest"):
            return (self.latest() != None)
        elif self.version.startswith("min"):
            return (self.min() != None)
        else:
            return (self.get_prop_vars("VARNAME") != None)

    def latest(self):
        assert(self.var.endswith(".latest"))
        sql="SELECT VARNAME FROM VARS WHERE VARNAME LIKE ? COLLATE NOCASE"
        var_nov = self.var_nov
        row = (f"{var_nov}%", )
        res = self.db_fetch(sql, row)
        versions = [ e[0].split('.',3)[2] for e in res ]
        versions.sort(key=int, reverse=True)
        if versions:
            return f"{var_nov}.{versions[0]}"
        else:
            return None

    def min(self):
        assert(self.version.startswith("min"))
        minver = self.minversion
        sql="SELECT VARNAME FROM VARS WHERE VARNAME LIKE ? COLLATE NOCASE"
        var_nov = self.var_nov
        row = (f"{var_nov}%", )
        res = self.db_fetch(sql, row)
        versions = [ e[0].split('.',3)[2] for e in res ]
        versions = [ int(v) for v in versions if int(v) >= minver ]
        versions.sort(key=int, reverse=True)
        if versions:
            return f"{var_nov}.{versions[0]}"
        else:
            return None

    def get_prop_vars(self, prop_name):

        sql = f"SELECT {prop_name} FROM VARS WHERE VARNAME=?"
        row = (self.var,)
        res = self.db_fetch(sql, row)
        if res:
            return res[0][0]
        else:
            return None

    def get_prop_files(self, filename:str, prop_name:str):
        sql = f"SELECT {prop_name} FROM FILES WHERE FILENAME=? AND VARNAME=?"
        row = (filename, self.var)
        res = self.db_fetch(sql, row)
        if res:
            return res[0][0]
        else:
            return None

    def get_dep(self):
        sql = f"SELECT DISTINCT DEPVAR FROM DEPS WHERE VAR=?"
        row = (self.var,)
        res = self.db_fetch(sql, row)
        res = sorted([ e[0] for e in res ], key = str.casefold)
        return res if res else []

    def rec_dep(self, stop = True):
        def rec(var:VarFile, depth=0):
            msg = " " * depth + f"Checking dep of {var.var}"
            if not var.exists():
                warn(f"{msg:<130}" + ": Not Found")
                if stop:
                    raise VarNotFound(var.var)
            else:
                info(f"{msg:<130}" + ":     Found")
            sql = f"SELECT DISTINCT DEPVAR FROM DEPS WHERE VAR=?"
            row = (var.var,)
            res = self.db_fetch(sql, row)
            res = sorted([ e[0] for e in res ])
            for varfile in res:
                try:
                    depvar = VarFile(varfile, use_db=True)
                except (VarExtNotCorrect, VarNameNotCorrect, VarVersionNotCorrect):
                    error(f"We skipped a broken dependency from {self.var}")
                    continue
                rec(depvar, depth+1 )
        rec(self)

    def db_files(self, with_meta = True):
        sql = f"SELECT FILENAME FROM FILES WHERE VARNAME=?"
        if not with_meta:
            sql = sql + " AND FILENAME NOT LIKE '%meta.json'"
        row = (self.var,)
        res = self.db_fetch(sql, row)
        if res:
            return sorted([ e[0] for e in res ])
        else:
            return []

    def db_delete(self):
        row = (self.var,)
        sql = f"DELETE FROM VARS WHERE VARNAME=?"
        self.db_exec(sql, row)
        sql = f"DELETE FROM FILES WHERE VARNAME=?"
        self.db_exec(sql, row)
        sql = f"DELETE FROM DEPS WHERE VAR=?"
        self.db_exec(sql, row)

    def get_file_cksum(self, filename):
        return self.get_prop_files(filename, "CKSUM")

    def get_file_size(self, filename):
        return self.get_prop_files(filename, "SIZE")

    def get_numfiles(self, with_meta = False):
        sql = f"SELECT COUNT(*) FROM FILES WHERE VARNAME == ?"
        if not with_meta:
            sql = sql + " AND FILENAME != 'meta.json'"
        row = (self.var, )
        return self.db_fetch(sql, row)[0][0]

    def get_refvar_forfile(self, file):
        cksum = self.get_file_cksum(file)
        sql = f"SELECT VARNAME, FILENAME FROM FILES WHERE CKSUM=? AND ISREF='YES' AND VARNAME!=? AND FILENAME LIKE ? GROUP BY VARNAME"
        row = (cksum, self.var, f"%{Path(file).name}")
        res = self.db_fetch(sql, row)
        if res:
            return res
        else:
            return None

    @property
    def license(self):
        return self.get_prop_vars("LICENSE")

    @property
    def size(self):
        return self.get_prop_vars("SIZE")

    @property
    def get_ref(self):
        return self.get_prop_vars("ISREF")

    @property
    def get_modtime(self):
        return self.get_prop_vars("MODIFICATION_TIME")

    @property
    def get_cksum(self):
        return self.get_prop_vars("CKSUM")
