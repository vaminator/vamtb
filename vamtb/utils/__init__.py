import json
import re
import os
import zipfile
import binascii
from functools import wraps
from pathlib import Path
from vamtb.log import *
from vamtb.vamex import *

# Constants
C_YAML = "vamtb.yml"
C_DDIR = "graph"
C_BAD_DIR = "00Dep"
C_REF_CREATORS = (
"50shades", "AcidBubbles", "AmineKunai", "AnythingFashionVR","AshAuryn",
"bvctr", "CosmicFTW","Errarr","GabiRX","geesp0t","hazmhox","Hunting-Succubus",
"Jackaroo","Jakuubz","JoyBoy","kemenate", "LFE","MacGruber","MeshedVR","Miki","Molmark","NoStage3","Oeshii",
"Roac","SupaRioAmateur", "TenStrip", "TGC", "VL_13")
C_NEXT_CREATOR = 127
C_DB = "vars.db"
C_DOT = "c:\\Graphviz\\bin\\dot.exe"
C_MAX_FILES = 50
C_MAX_SIZE = 20 * 1024 * 1024

def prettyjson(obj):
    return json.dumps(obj, indent = 4)

def search_files_indir(fpath, pattern):
    pattern = re.sub(r'([\[\]])','[\\1]',pattern)
    return [ x for x in Path(fpath).glob(f"**/{pattern}") if x.is_file() ]

def crc32c(content):
    buf = (binascii.crc32(content) & 0xFFFFFFFF)
    return "%08X" % buf

def zipdir(path, zipname):
    debug("Repacking var...")
    with zipfile.ZipFile(zipname, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(path):
            for file in files:
                zipf.write(os.path.join(root, file), 
                        os.path.relpath(os.path.join(root, file), 
                                        os.path.join(path, '.')))

def toh(val: int) ->str:
    if val > 1024 * 1024 * 1024:
        return f"{round(val/(1024*1024*1024), 3)}GB"
    elif val > 1024 * 1024:
        return f"{round(val/(1024*1024), 3)}MB"
    elif val > 1024:
        return f"{round(val/(1024), 3)}KB"
    else:
        return val

def id_is_ref(id:str):
    if id in ("id", "uid"):
        return True
    if id.endswith("Url"):
        return True
    if id.startswith("plugin#"):
        return True
    if id.startswith("customTexture_"):
        return True
    if id == "simTexture":
        return True
    return False

def ensure_binaryfiles(refi, prefix):
    alt = { 'vmi': 'vmb', 'vam': 'vab', 'vap': 'vapb'}
    # ralt = { alt[e]:e for e in alt }
    assert (prefix in list(alt))

    refo = {}
    for fn in refi:
        if fn.endswith("." + prefix):
            fnb = Path(fn).with_suffix("." + alt[prefix]).as_posix()
            if fnb not in refi:
                debug(f"We found a reference for {fn} but not its counterpart {fnb}")
                continue
            refo[fn] = refi[fn]
            refo[fnb] = refi[fnb]
        elif fn.endswith(f".{alt[prefix]}"):
            fni = Path(fn).with_suffix("." + prefix).as_posix()
            if fni not in refi:
                debug(f"We found a reference for {fn} but not its counterpart {fni}")
                continue
            refo[fn] = refi[fn]
            refo[fni] = refi[fni]
        else:
            refo[fn] = refi[fn]
    return refo

def get_filepattern(ctx):
    file = ctx.obj['file']
    if file:
        if "%" in file:
            pattern = file.replace("%", "*")
        else:
            pattern = f"*{file}*"
    else:
        pattern = "*.var"
    return ctx.obj['file'] if 'file' in ctx.obj else None, ctx.obj['dir'], pattern

def catch_exception(func=None):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except VarNotFound as e:
            error(f"Var not found:{e}")
        except VarFileNameIncorrect as e:
            error(f"Var filename incorrect:{e}")
    return wrapper

def del_empty_dirs(target_path):
    for p in Path(target_path).glob('**/*'):
        if p.is_dir() and len(list(p.iterdir())) == 0:
            try:
                os.removedirs(p)
            except:
                pass
