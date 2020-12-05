'''Vam dir structure'''
import logging
import glob
import shutil
from pathlib import Path

def find_dir_i(fpath, fbase):
    """ Finds a given directory """
    logging.debug("Searching for %s/**/%s" % (fbase,fpath))
    for mpath in glob.iglob(str(Path(fbase, "**", fpath)), recursive=True):
        yield mpath

def organize(pattern, src, dst):
    dst = Path(dst,"Saves",pattern).resolve().parents[3]
    for p in find_dir_i(pattern, src):
        p = Path(p).resolve().parents[2]
        print("Moving %s to %s" % (p, dst))
        exit()

# Duh windows
#        shutil.move(str(p),"%s\\" %dst)
# Duh python (some jerk decided to always strip leading slashes yet shutil relies on it)
        shutil.copytree(str(p),"%s\\" % dst, dirs_exist_ok=True)
        shutil.rmtree(str(p))
        exit()
