'''Vam dir structure'''
import logging
from pathlib import Path
import re
import os
import zipfile
from vamtb import varfile
from vamtb import vamex

def is_vamdir(fpath):
    logging.debug("Checking if %s is a VAM dir" % fpath)
    return Path("%s/AddonPackages" % fpath).exists()

def list_vars(fpath, pattern = "*.var"):
    logging.debug(f"Listing files pattern **/{pattern} in {fpath}")
    pattern = re.sub(r'([\[\]])','[\\1]',pattern)
    return list( x for x in Path(fpath).glob(f"**/{pattern}") if x.is_file())

def stats_vars(fpath, pattern = None):
    logging.debug("Listing files pattern %s/%s" % (fpath, pattern))
    pattern = re.sub(r'([\[\]])','[\\1]',pattern)
    return list( x for x in Path(fpath).glob(f"**/{pattern}") if x.is_file())

def find_var(dir, varname):
    logging.debug("Searching for var %s in %s" % (varname, dir))
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

def recurse_dep(dir, var, do_print=False):
    def recdef(var, depth=0):
        if do_print:
            print("%sChecking dependencies of %s" % (" "*depth, var))
        else:
            logging.info("%sChecking dependencies of %s" % (" "*depth, var))
        depth += 1

        deps = varfile.dep_fromvar(dir, var)
        for dep in deps:
            try:
                _ = find_var(dir, dep)
                logging.debug("%sSearching dep %s: OK"%(" "*depth, dep))
            except vamex.VarNotFound:
                logging.debug("%sSearching dep %s: NOT FOUND"%(" "*depth, dep))
                raise
            if do_print:
                print("%sDep: %s -> %s" % (" "*depth, dep, find_var(dir, dep)))
            try:
                recdef(dep, depth + 1)
            except RecursionError:
                # TODO: detect from which var the loop is created move that var
                raise
    recdef(var)

def create_dir(infile, newdir):
    """
    Create newdir directory
    Detect from in_file what type of content
    Create subtree in newdir
    Copy files linked to infile inside newdir
    """
    Path(newdir).mkdir(parents=True, exist_ok=True)
    logging.debug(f"Directory {newdir} created")
    

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
