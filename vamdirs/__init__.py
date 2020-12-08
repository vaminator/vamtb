'''Vam dir structure'''
import logging
from pathlib import Path
import re
import varfile
import vamex

def is_vamdir(fpath):
    logging.debug("Checking if %s is a VAM dir" % fpath)
    return Path("%s/AddonPackages" % fpath).exists()

def list_vars(fpath, pattern = "*.var"):
    logging.debug(f"Listing files pattern **/{pattern} in {fpath}")
    pattern = rf"**/{pattern}"
    return list( x for x in Path(fpath).glob(pattern) if x.is_file())

def stats_vars(fpath, pattern = "*.var"):
    logging.debug("Listing files pattern %s/%s" % (fpath, pattern))
    pattern = "**/%s" % re.escape(pattern)
    return list( x for x in Path(fpath).glob(pattern) if x.is_file())

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

def recurse_dep(dir, var, do_print=False, movepath=None):
    def recdef(dir, var, do_print, depth):
        if do_print:
            print("%sChecking dependencies of %s" % (" "*depth, var))
        else:
            logging.info("%sChecking dependencies of %s" % (" "*depth, var))
        depth += 1
        try:
            var_file = find_var(dir, varname = var)
        except vamex.VarNotFound:
            # This happens if file names contain weird chars for windows
            # FIXME
            logging.error("%sNot found - %s"%(" "*depth, var))
#            Path(var).rename(Path(movepath, var_file.name))
            raise
        except vamex.VarNameNotCorrect:
            if do_print:
                logging.error("%sName not correct - %s"%(" "*depth, var))
            raise
        except Exception as e:
            logging.error("Uncaught exc %s"%e)
            raise

        try:
            meta = varfile.extract_meta_var(var_file)
        except vamex.VarMetaJson:
            logging.error(f'{" "*depth}Failed to decode meta in {var_file}')
            raise

        if not( "dependencies" in meta and meta['dependencies']):
            if do_print:
                print("%sDep: None" % (" "*depth))
            return
        for dep in meta['dependencies']:
            try:
                _ = find_var(dir, dep)
                logging.debug("%sSearching dep %s: OK"%(" "*depth, dep))
            except vamex.VarNotFound as e:
                logging.error("%sSearching dep %s: NOT FOUND"%(" "*depth, dep))
                raise
            if do_print:
                print("%sDep: %s -> %s" % (" "*depth, dep, find_var(dir, dep)))
            try:
                recdef(dir, dep, do_print, depth + 1)
            except RecursionError:
                # TODO: detect from which var the loop is created move that var
                raise
    recdef(dir, var, do_print, 0)

def create_dir(infile, newdir):
    """
    Create newdir directory
    Detect from in_file what type of content
    Create subtree in newdir
    Copy files linked to infile inside newdir
    """
    Path(newdir).mkdir(parents=True, exist_ok=True)
    logging.debug(f"Directory {newdir} created")
    