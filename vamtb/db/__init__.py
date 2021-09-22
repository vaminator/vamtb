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

def init_dbs(conn):
    conn.execute('''CREATE TABLE IF NOT EXISTS VARS
         (VARNAME TEXT PRIMARY KEY     NOT NULL,
         ISREF TEXT NOT NULL,
         CREATOR TEXT NOT NULL,
         VERSION INT NOT NULL,
         LICENSE TEXT NOT NULL,
         MODIFICATION_TIME    INT     NOT NULL,
         CKSUM   CHAR(4) NOT NULL);''')

    conn.execute('''CREATE TABLE IF NOT EXISTS DEPS
         (ID INTEGER PRIMARY KEY AUTOINCREMENT,
         VAR TEXT NOT NULL,
         DEP TEXT NOT NULL);''')

    conn.execute('''CREATE TABLE IF NOT EXISTS FILES
         (ID INTEGER PRIMARY KEY AUTOINCREMENT,
         FILENAME TEXT NOT NULL,
         ISREF TEXT NOT NULL,
         VARNAME TEXT NOT NULL,
         CKSUM   CHAR(4) NOT NULL);''')

ref_creators = (
"50shades", "AcidBubbles", "AmineKunai", "AnythingFashionVR","AshAuryn",
"bvctr", "CosmicFTW","Errarr","GabiRX","geesp0t","hazmhox","Hunting-Succubus",
"Jackaroo","JoyBoy","kemenate", "LFE","MacGruber","MeshedVR","Miki","Molmark","NoStage3","Oeshii",
"Roac","SupaRioAmateur", "TenStrip", "TGC", "VL_13")

def store_var(conn, var):
    """ Insert (if NE) or update (if Time>) or do nothing (if Time=) """
    varname = var.name

    cur = conn.cursor()
    cur.execute("SELECT * FROM VARS WHERE VARNAME=?", (varname,))
    rows = cur.fetchall()
    if not rows:
        modified_time = os.path.getmtime(var)
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
        sql = """INSERT INTO DEPS(ID,VAR,DEP) VALUES (?,?,?)"""
        for dep in varfile.dep_fromvar(dir=None, var=var, full=True):
            row = (None, varname[0:-4], dep)
            cur = conn.cursor()
            cur.execute(sql, row)
    else:
        assert(len(rows) == 1)
        db_varname, db_isref, db_creator, db_version, db_license, db_modtime, db_cksum = rows[0]
        modified_time = os.path.getmtime(var)
        if db_modtime < modified_time:
            logging.error("Update of database not done, erase database file and rerun vamtb dbs")
            logging.error(f"This could also be because you have duplicate var for {varname} (in that case, use vamtb sortvar) ")
            exit(0)
        else:
            logging.debug(f"Var {varname} already in database")


def store_vars(vars_list, sync = True):
    conn = sqlite3.connect('vars.db')
    init_dbs(conn)
    progress_iterator = tqdm(vars_list, desc="Writing database…", ascii=True, maxinterval=5, ncols=75, unit='var')
    for var in progress_iterator:
        logging.debug(f"Checking var {var}")
        store_var(conn, var)
        if sync:
            conn.commit()
    logging.info(f"{len(vars_list)} var files stored")

    # Commit only at the end to speed things up but you need more RAM
    conn.commit()
    conn.close()

def get_prop_vars(conn, varname, prop_name):
    cur = conn.cursor()
    sql = f"SELECT {prop_name} FROM VARS WHERE VARNAME=?"
    row = (varname,)
    cur.execute(sql, row)
    res = cur.fetchall()
    if res:
        return res[0][0]
    else:
        return None

def get_prop_files(conn, filename, varname, prop_name):
    cur = conn.cursor()
    sql = f"SELECT {prop_name} FROM FILES WHERE FILENAME=? AND VARNAME=?"
    row = (filename, varname)
    cur.execute(sql, row)
    res = cur.fetchall()
    if res:
        return res[0][0]
    else:
        return None

def get_file_cksum(conn, filename, varname):
    return get_prop_files(conn, filename, varname, "CKSUM")

def get_license(conn, varname):
    if not varname.endswith(".var"):
        varname = f"{varname}.var"
    return get_prop_vars(conn, varname, "LICENSE")

def get_ref(conn, varname):
    return get_prop_vars(conn, varname, "ISREF")

def var_exists(conn, varname):
    if not varname.endswith(".var"):
        varname = f"{varname}.var"
    if varname.endswith(".latest"):
        return (latest(conn, varname) != None)
    else:
        return (get_prop_vars(conn, varname, "VARNAME") != None)

def get_depending_var_from_file(conn, filename):
    var, file = filename.split(':')
    if var.endswith(".var"):
        var = var[0:-4]
    filename = f"{var}:{file}"

    cur = conn.cursor()
    sql = f"SELECT VAR FROM DEPS WHERE DEP=?"
    row = (filename,)
    cur.execute(sql, row)
    res = cur.fetchall()

    a,b,c = var.split('.')
    default_var_filename = f"{a}.{b}.latest:{file}"
    sql = f"SELECT VAR FROM DEPS WHERE DEP=?"
    row = (default_var_filename,)
    cur.execute(sql, row)
    res2 = cur.fetchall()

    res.extend(res2)

    return [ v[0] for v in res ]

def isfile_invar(conn, mfile, var):
    cur = conn.cursor()
    sql="SELECT FILENAME FROM FILES WHERE FILENAME = ? AND VARNAME = ?"
    cur.execute(sql, (mfile, var))
    if cur.fetchall():
        return True
    else:
        return False

def latest(conn, var):
    #Remove version and extension 
    var = ".".join(var.split('.',2)[0:2])

    cur = conn.cursor()
    sql="SELECT VARNAME FROM VARS WHERE VARNAME LIKE ? COLLATE NOCASE"
    row=(f"{var}%", )
    cur.execute(sql, row)

    versions = [ e[0].split('.',3)[2] for e in cur.fetchall() ]
    versions.sort(key=int, reverse=True)
    if versions:
        return f"{var}.{versions[0]}"
    else:
        return None

desc_deps=[]

def deps_desc_node(conn, var):
    global desc_deps

    cur = conn.cursor()
    sql="SELECT DEP FROM DEPS WHERE VAR = ? COLLATE NOCASE"
    row = (var, )
    cur.execute(sql, row)

    uniq = set()

    for depvar in [ e[0].split(':')[0] for e in cur.fetchall() ]:
        if "latest" in depvar:
            ldepvar = latest(conn, depvar)
            if ldepvar is not None:
                depvar = ldepvar
        uniq.add(depvar)
    desc_deps.extend(uniq)

    for dep in sorted([ v for v in uniq if v not in desc_deps ]):
        desc_deps.extend(deps_desc_node(conn, dep))
    return desc_deps

asc_deps=[]
def deps_asc_node(conn, var):
    global asc_deps

    cur = conn.cursor()
    sql = "SELECT DISTINCT VAR FROM DEPS WHERE DEP LIKE ? OR DEP LIKE ? COLLATE NOCASE"
    var_nov = ".".join(var.split('.')[0:2])
    row = (f"{var_nov}.latest:%", f"{var}:%")
    cur.execute(sql, row)

    asc = [ e[0] for e in cur.fetchall() ]
    asc = [ e for e in asc if not e.endswith(".latest") or latest(conn, e) == e ]
    asc_deps.extend(set(asc))

    for ascx in sorted([ e for e in asc if e != var and e not in asc_deps ]):
        asc_deps.extend(deps_asc_node(conn, ascx))
    return set(asc_deps)

def deps_node(conn, var):
    """Get dependent and ascendant nodes"""
    global asc_deps
    global desc_deps
    asc_deps=[]
    desc_deps=[]
    depd = set(deps_desc_node(conn, var))
    depa = set(deps_asc_node(conn, var))
    dep = {var} | depd | depa
    return sorted(dep, key=str.casefold)

def set_props(conn, var_list):
    res = []
    for var in var_list:
        if var_exists(conn, var):
            res.append(f'"{var}" [color=blue];')
        else:
            res.append(f'"{var}" [color=red];')
        license = get_license(conn, var)
        if license in ("PC", "Questionable"):
            res.append(f'"{var}" [shape=box];')
    return res

def dotty(lvar=None):

    direct_graphs=[]
    shapes = []
    
    conn = sqlite3.connect('vars.db')
    if lvar:
        only_nodes = deps_node(conn, lvar)
    cur = conn.cursor()
    sql="SELECT VAR, DEP FROM DEPS"
    cur.execute(sql)
    the_deps = cur.fetchall()
    for var, depf in the_deps:
        dep = None
        if "latest" in depf:
            dep = ".".join(depf.split(".", 2)[0:2])
            dep = latest(conn, dep)
        if not dep:
            dep = depf.split(':',1)[0]
        if lvar and not(dep in only_nodes and var in only_nodes):
            continue
        if f'"{var}" -> "{dep}";' not in direct_graphs:
            logging.debug(f"Adding {var} -> {dep}")
            props = set_props(conn, [var, dep])
            shapes.extend(props)
            direct_graphs.append(f'"{var}" -> "{dep}";')

    if direct_graphs:
        dot_lines = shapes 
        dot_lines.extend(sorted(list(set(direct_graphs))))

        with open("deps.dot", "w") as f:
            f.write("digraph vardeps {" + "\n" + 
            "\n".join(dot_lines) + "\n" + 
            "}")

        pdfname = f"VAM_{lvar}.pdf" if lvar else "VAM_deps.pdf"
        try:
            subprocess.check_call(f'c:\\Graphviz\\bin\\dot.exe -Gcharset=latin1 -Tpdf -o "{pdfname}" deps.dot')
        except Exception as CalledProcessError:
            logging.error("You need dot from graphviz installed in c:\\Graphviz\\bin\\dot.exe")
            os.unlink("deps.dot")
            exit(0)
        os.unlink("deps.dot")
        logging.info("Graph generated")

    else:
        logging.warning("No graph as no var linked to it")
