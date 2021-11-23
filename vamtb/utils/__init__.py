import json
import re
import os
import zipfile
import binascii
from pathlib import Path
from vamtb.log import *

# Conf
C_YAML = "vamtb.yml"
C_DDIR = "graph"
C_BAD_DIR = "00Dep"
C_REF_CREATORS = (
"50shades", "AcidBubbles", "AmineKunai", "AnythingFashionVR","AshAuryn",
"bvctr", "CosmicFTW","Errarr","GabiRX","geesp0t","hazmhox","Hunting-Succubus",
"Jackaroo","JoyBoy","kemenate", "LFE","MacGruber","MeshedVR","Miki","Molmark","NoStage3","Oeshii",
"Roac","SupaRioAmateur", "TenStrip", "TGC", "VL_13")
C_DB = "vars.db"
C_DOT = "c:\\Graphviz\\bin\\dot.exe"

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
