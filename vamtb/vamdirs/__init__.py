'''Vam dir structure'''
import logging
from pathlib import Path
import re
import os
import zipfile
from vamtb import varfile
from colorama import Fore, Back, Style
from vamtb import vamex
from vamtb.utils import *

def is_vamdir(fpath):
    logging.debug("Checking if %s is a VAM dir" % fpath)
    return Path("%s/AddonPackages" % fpath).exists()

def list_vars(fpath, pattern = "*.var"):
    # logging.debug(f"Listing files pattern **/{pattern} in {fpath}")
    pattern = re.sub(r'([\[\]])','[\\1]',pattern)
    l = Path(fpath).glob(f"**/{pattern}*")
    lfile = [ x for x in l if x.is_file()]
    return lfile

def stats_vars(fpath, pattern = None):
    # logging.debug("Listing files pattern %s/%s" % (fpath, pattern))
    pattern = re.sub(r'([\[\]])','[\\1]',pattern)
    return list( x for x in Path(fpath).glob(f"**/{pattern}") if x.is_file())

def find_var(dir, varname):
    # logging.debug("Searching for var %s in %s" % (varname, dir))
    if varname.endswith(".var"):
        varname=varname[0:-4]
    try:
        varfile.is_namecorrect(Path("%s.foo" % varname), checksuffix=False)
    except vamex.VarNameNotCorrect:
        raise
    creator, content, version = varname.split('.')
    numversion = True
    try:
        _=int(version)
    except ValueError:
        if not( version == "latest" or version.startswith('min')):
            logging.error("Var %s has incorrect version (%s)" % (varname, version))
            raise vamex.VarVersionNotCorrect(varname)
        numversion = False

    if numversion:
        pattern = "%s.var" % varname
    else:
        pattern = "%s.%s.*.var" % (creator, content)
    vars = list_vars(dir, pattern = pattern)
    if numversion:
        if len(vars) > 1:
            logging.warning("Found several files corresponding to %s, returning first one" % varname)
    else:
        vars = list(reversed(sorted(vars, key=lambda item: item.name)))
    if vars:
        return vars[0]
    else:
        raise vamex.VarNotFound(varname)

def exists_var(dir, varname):
    mlevel = logging.root.level
    logging.root.setLevel(level = logging.ERROR)
    found = True
    try:
        find_var(dir, varname)
    except:
        found = False
    logging.root.setLevel(level = mlevel)
    return found

def recurse_dep(dir, var, do_print=False, strict=False):
    def recdef(var, depth=0):
        try:
            deps = varfile.dep_frommeta(dir, var)
        except vamex.VarMetaJson:
            print(ucol.redf("%sUnknown dependencies for %s: Couldn't decode json" % (" "*depth, var) ))
        except vamex.VarNotFound:
            logging.error("Var not found!")
            if strict:
                raise
            else:
                return
        if not deps:
            logging.debug("%s0 dependencies for %s" % (" "*depth, var))
            return
        if do_print:
            print("%s%s dependencies for %s: %s" % (" "*depth, "Checking %s"%len(deps) if deps else "No", var, ",".join(deps.keys()) or ""))
        else:
            logging.info("%s%s dependencies of %s: %s" % (" "*depth, "Checking %s"%len(deps) if deps else "No", var, ",".join(deps.keys()) or ""))
        depth += 2
        for dep in deps:
            try:
                _ = find_var(dir, dep)
                logging.debug(ucol.greenf("%sSearching dep %s: OK"%(" "*depth, dep) ))
            except vamex.VarNotFound:
                logging.debug(ucol.redf("%sSearching dep %s: NOT FOUND"%(" "*depth, dep) ))
                if strict:
                    raise
                else:
                    continue
            if do_print:
                print("%sDep: %s -> %s" % (" "*depth, dep, find_var(dir, dep)))
            try:
                recdef(dep, depth + 1)
            except RecursionError:
                # TODO: detect from which var the loop is created move that var
                raise
    recdef(var)


def zipdir(path, zipname):
    logging.debug("Repacking var...")
    zipf = zipfile.ZipFile(zipname, 'w', zipfile.ZIP_DEFLATED)
    # ziph is zipfile handle
    for root, dirs, files in os.walk(path):
        for file in files:
            zipf.write(os.path.join(root, file), 
                       os.path.relpath(os.path.join(root, file), 
                                       os.path.join(path, '.')))
    zipf.close()
