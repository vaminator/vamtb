import json
import re
import os
import zipfile
import binascii
from functools import wraps
from pathlib import Path
from datetime import datetime
from vamtb.log import *
from vamtb.vamex import *

# Constants
C_YAML = "vamtb.yml"
C_DDIR = "graph"
C_BAD_DIR = "00Dep"
C_REF_CREATORS = (
"50shades", "AcidBubbles", "AmineKunai", "AnythingFashionVR","AshAuryn",
"bvctr", "CosmicFTW","Errarr","GabiRX","geesp0t","hazmhox","Hunting-Succubus",
"Jackaroo","Jakuubz","kemenate", "klphgz", "LFE","MacGruber","MeshedVR","Miki","Molmark","Morph","NoStage3","Oeshii",
"prestigitis", "RenVR", "Roac","SupaRioAmateur", "TenStrip", "TGC", "VL_13",)

# Creators which you don't consider a pure reference creator but still have a few general packs
C_REF_VARPATTERNS = (
    "Damarmau.DAMAR_morphs.", "Damarmau.Damar_Textures.", "vecterror._Morphs2021."
    )

C_CREATORS_ALIAS = {
    "splineVR": [ "s p l i n e  VR", "s p l i n e VR", "s_p_l_i_n_e_VR"],
    "MrCadillacV8": ["Mr_CadillacV8"],
    "MK47": "MK_47",
    "MareProductions": [ "Mare_Productions", "Mare Productions"],
    "Anonymous": ["AnonymousPerson", "Anon"],
    "Oeshii": ["oeshi"]
}

C_NEXT_CREATOR = 127
C_DB = "vars.db"
C_DOT = "c:\\Graphviz\\bin\\dot.exe"
C_MAX_FILES = 50
C_MAX_SIZE = 20 * 1024 * 1024

def prettyjson(obj):
    return json.dumps(obj, indent = 4)

def search_files_indir(fpath, pattern, ign = False):
    pattern = re.sub(r'([\[\]])','[\\1]',pattern)
    res = [ x for x in Path(fpath).glob(f"**/{pattern}") if x.is_file() ]
    if not ign and not res:
        warn("No files found matching pattern")
    return res

def crc32c(content):
    buf = (binascii.crc32(content) & 0xFFFFFFFF)
    return "%08X" % buf

def zipdir(path, zipname):
    debug("Repacking var...")
    with zipfile.ZipFile(zipname, 'w', zipfile.ZIP_DEFLATED) as zipf:
        zipf.comment = f"Repacked on {datetime.now().strftime('%Y%m%dT%H%M%S')}".encode('ascii')
        # zipf.compresslevel = 1
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
    alt = { 'vmi': 'vmb', 'vam': 'vab', 'vap': 'vapb', 'vaj': 'vab'}
    # ralt = { alt[e]:e for e in alt }
    assert (prefix in list(alt))

    refo = {}
    for fn in refi:
        if fn.endswith("." + prefix):
            fnb = Path(fn).with_suffix("." + alt[prefix]).as_posix()
            if not(fnb in refi and refi[fnb]['newvar'] == refi[fn]['newvar']):
                debug(f"We found a reference for {fn} but not its counterpart {fnb}")
                continue
            refo[fn] = refi[fn]
            refo[fnb] = refi[fnb]
        elif fn.endswith(f".{alt[prefix]}"):
            fni = Path(fn).with_suffix("." + prefix).as_posix()
            if not(fni in refi and refi[fni]['newvar'] == refi[fn]['newvar']):
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
            pattern = file
        if not pattern.endswith(".var"):
            pattern = pattern + ".var"
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
        except zipfile.BadZipFile as e:
            error(f"Var has CRC problems:{e}")
    return wrapper

def del_empty_dirs(target_path):
    for p in Path(target_path).glob('**/*'):
        if p.is_dir() and len(list(p.iterdir())) == 0:
            try:
                os.removedirs(p)
            except:
                pass

def ia_identifier(s:str)->str:
    return "vam1__"  + s.replace(' ','_').replace('&', '_').replace("'", "_")

def get_license_url(s):
    license_url = {
        "CC BY": "https://creativecommons.org/licenses/by/4.0/",
        "CC BY-NC": "https://creativecommons.org/licenses/by-nc/4.0",
        "CC BY-NC-ND": "https://creativecommons.org/licenses/by-nc-nd/4.0",
        "CC BY-ND": "https://creativecommons.org/licenses/by-nd/4.0",
        "CC BY-SA": "https://creativecommons.org/licenses/by-sa/4.0",
        "CC BY-NC-SA" : "http://creativecommons.org/licenses/by-nc-sa/4.0/",
        }

    return license_url.get(s, None)