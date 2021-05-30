'''Vam dir structure'''
import os
import logging
import re
import sqlite3
from pathlib import Path
from vamtb import varfile
from vamtb import vamex
from zipfile import ZipFile, BadZipFile

def init_dbs(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS VARS
         (VARNAME TEXT PRIMARY KEY     NOT NULL,
         ISREF TEXT NOT NULL,
         CREATOR TEXT NOT NULL,
         VERSION INT NOT NULL,
         LICENSE TEXT NOT NULL,
         MODIFICATION_TIME    INT     NOT NULL,
         CKSUM   CHAR(4) NOT NULL);''')

    conn.execute('''CREATE TABLE IF NOT EXISTS FILES
         (ID INTEGER PRIMARY KEY AUTOINCREMENT,
         FILENAME TEXT NOT NULL,
         ISREF TEXT NOT NULL,
         VARNAME TEXT NOT NULL,
         CKSUM   CHAR(4) NOT NULL);''')

ref_creators = (
"50shades", "AcidBubbles", "AmineKunai", "AnythingFashionVR","AshAuryn",
"CosmicFTW","Errarr","GabiRX","geesp0t","hazmhox","Hunting-Succubus",
"Jackaroo","JoyBoy","LFE","MacGruber","MeshedVR","Miki","Molmark","Oeshii",
"Roac","SupaRioAmateur","VL_13")

def store_var(conn, var):
    """ Insert (if NE) or update (if Time>) or do nothing (if Time=) """
    modified_time = os.path.getmtime(var)
    varname = var.name

    cur = conn.cursor()
    cur.execute("SELECT * FROM VARS WHERE VARNAME=?", (varname,))
    rows = cur.fetchall()
    if not rows:
        creator, version, modified_time,cksum=varfile.get_props(var)
        if creator in ref_creators:
            v_isref="YES" 
        else:
            v_isref="UNKNOWN"
        meta=varfile.extract_meta_var(var)
        license=meta['licenseType']
        row = (varname, v_isref, creator, version, license, modified_time, cksum)
        sql = """INSERT INTO VARS(VARNAME,ISREF,CREATOR,VERSION,LICENSE,MODIFICATION_TIME,CKSUM) VALUES (?,?,?,?,?,?,?)"""
        cur = conn.cursor()
        cur.execute(sql, row)
        with ZipFile(var, mode='r') as myvar:
            listOfFileNames = myvar.namelist()
            for f in listOfFileNames:
                # logging.debug(f"Computing crc of {f}")
                with myvar.open(f) as fh:
                    try:
                        crcf = varfile.crc32c(fh.read())
                    except:
                        #FIXME zlib.error: Error -3 while decompressing data: invalid code lengths set
                        return
                if creator in ref_creators:
                    f_isref="YES" 
                else:
                    f_isref="UNKNOWN"
                row = (None, f, f_isref, varname, crcf)
                sql = """INSERT INTO FILES (ID,FILENAME,ISREF,VARNAME,CKSUM) VALUES (?,?,?,?,?)"""
                cur = conn.cursor()
                cur.execute(sql, row)
        logging.debug(f"Stored var {varname} and files in databases")

    else:
        assert(len(rows) == 1)
        db_varname, db_isref, db_creator, db_version, db_license, db_modtime, db_cksum = rows[0]
        if db_modtime < modified_time:
            logging.error("Update of database not done, erase database file and rerun vamtb dbs")
            assert(False)
        else:
            logging.debug(f"Var {varname} already in database")


def store_vars(vars_list):
    conn = sqlite3.connect('vars.db')
    init_dbs(conn)
    for var in vars_list:
        logging.debug(f"Storing var {var}")
        store_var(conn, var)
    # Commit at the end to speed things up but you need more RAM
    conn.commit()
    conn.close()

def find_common_files(conn, dup_varname, ref_varname):
    """
    returns a list of [dup_file, ref_file]
    dup_file is SELF:/path/to/file
    ref_file is ref_varname:/other/file
    with ref_varname being .latest
    """
    result=list()
    dup_varname=f"{dup_varname}.var"
    ref_varname=f"{ref_varname}.var"
    creator, asset, version,_ = ref_varname.split(".", 4)
    ref_varname_latest = ".".join((creator, asset, "latest"))

    sql="SELECT * FROM FILES WHERE VARNAME == ? AND FILENAME != ? AND CKSUM != ?"
    row = (dup_varname,"meta.json", "00000000")
    cur = conn.cursor()
    cur.execute(sql, row)
    dup_var_files=cur.fetchall()
    for dup_var_file in dup_var_files:
        _, dup_filename, _, _, dup_cksum = dup_var_file
        dup_filenamebase = Path(dup_filename).name
        sql = """SELECT * FROM FILES WHERE FILENAME LIKE ? AND CKSUM == ? AND VARNAME == ?"""
        row = (f"%{dup_filenamebase}%", dup_cksum, ref_varname)
        cur = conn.cursor()
        # logging.debug(f"Looking for file {dup_filenamebase} in {ref_varname}")
        cur.execute(sql, row)
        ref_var_file=cur.fetchall()
        if not ref_var_file:
            continue
        assert(len(ref_var_file) == 1)
        _, ref_filename, _, _, _ = ref_var_file[0]
        elt=(f"SELF:/{dup_filename}", f"{ref_varname_latest}:/{ref_filename}")
        result.append(elt)
    return result

def reref(conn, mdir, dup_varname, ref_varname, license):
    """
    This will reref files in dup_varname which are already in ref_varname
    """
    common_files = find_common_files(conn, dup_varname, ref_varname)
    for cf in common_files:
        logging.info(f"{cf[0]}-->{cf[1]}")
    varfile.reref(mdir, dup_varname, ref_varname, license, common_files)
    for f in common_files:
        sql="DELETE FROM FILES WHERE VARNAME=? AND FILENAME=?"
        row=(f"{dup_varname}.var", f[0].removeprefix("SELF:/"))
        cur = conn.cursor()
        cur.execute(sql, row)
    conn.commit()
    
def get_license(conn, varname):
    cur = conn.cursor()
    sql="SELECT LICENSE FROM VARS WHERE VARNAME=?"
    row=(varname,)
    cur = conn.cursor()
    cur.execute(sql, row)
    license = cur.fetchall()
    return license[0][0]

def find_dups(do_reref, mdir):
    rerefed=list()
    conn = sqlite3.connect('vars.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM FILES")
    db_files = cur.fetchall()
    for db_file in db_files:
        ref_id, ref_filename, ref_isref, ref_varname, ref_cksum = db_file
        ref_creator, asset, version, _ = ref_varname.split(".", 4)
        ref_varname = ".".join((ref_creator, asset, version))
        ref_filenamebase = Path(ref_filename).name
        if ref_cksum == "00000000":
            continue
        sql = """SELECT * FROM FILES WHERE ISREF != ? AND FILENAME LIKE ? AND CKSUM == ? AND ID != ? AND VARNAME NOT LIKE ?"""
        row = ("YES", f"%{ref_filenamebase}%", ref_cksum, ref_id, f"{ref_creator}%")
        cur = conn.cursor()
        cur.execute(sql, row)
        db_files_dup = cur.fetchall()
        if not db_files_dup:
            continue
        list_dup_varname = list(map(lambda x: x[3], db_files_dup))
        logging.info(f"Found {len(db_files_dup)} dups of {ref_varname} : '{ref_filename}' in vars {list_dup_varname}")
        for db_file_dup in db_files_dup:
            dup_id, dup_filename, dup_isref, dup_varname, dup_cksum = db_file_dup
            creator, asset, version, _ = dup_varname.split(".", 4)
            dup_varname = ".".join((creator, asset, version))
            logging.debug(f"Found dup of {ref_varname} : '{ref_filename}' in {dup_varname} : '{dup_filename}'")
            if do_reref and f"{dup_varname},{ref_varname}" not in rerefed:
                print(f"Reref {dup_varname} to use {ref_varname} [Y/N] ? ", end='')
                if (input() == "Y"):
                    ref_license=get_license(conn, f"{ref_varname}.var")
                    reref(conn, mdir, dup_varname, ref_varname, ref_license)
                rerefed.append(f"{dup_varname},{ref_varname}")
    