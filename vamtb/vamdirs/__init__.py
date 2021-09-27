'''Vam dir structure'''
import logging
from pathlib import Path
import re
import os
import zipfile
from vamtb import varfile
from colorama import Fore, Back, Style
from vamtb import vamex
from vamtb import utils
from vamtb.utils import *

class VaM:
    __AddonDir = None

    __instance = None
    __conn = None

    @staticmethod 
    def getInstance():
        """ Static access method. """
        if VaM.__instance == None:
            VaM()
        return VaM.__instance

    def __init__(self, dir):
        self.__AddonDir = self.toaddondir(dir)

    def AddonDir(self):
        return self.__AddonDir

    def toaddondir(self, dir):
        dir = Path(dir)
        if dir.is_dir():
            if dir.name != "AddonPackages":
                dir = Path(dir, "AddonPackages")
            if dir.exists():
                return dir
            else:
                return None
        else:
            return None

#    def search(self, pattern="*.var"):
#        fpath = self.__AddonDir
#        logging.debug(f"Listing files pattern **/{pattern} in {fpath}")
#        return utils.search_files_indir(self.__AddonDir, pattern)

    def stats_vars(self, fpath, pattern = None):
        # logging.debug("Listing files pattern %s/%s" % (fpath, pattern))
        pattern = re.sub(r'([\[\]])','[\\1]',pattern)
        return list( x for x in Path(fpath).glob(f"**/{pattern}") if x.is_file())

    def exists_var(self, dir, varname):
        mlevel = logging.root.level
        logging.root.setLevel(level = logging.ERROR)
        found = True
        try:
            self.find_var(dir, varname)
        except:
            found = False
        logging.root.setLevel(level = mlevel)
        return found

    def recurse_dep(self, dir, var, do_print=False, strict=False):
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
                    _ = vamdirs.f. find_var(dir, dep)
                    logging.debug(ucol.greenf("%sSearching dep %s: OK"%(" "*depth, dep) ))
                except vamex.VarNotFound:
                    logging.debug(ucol.redf("%sSearching dep %s: NOT FOUND"%(" "*depth, dep) ))
                    if strict:
                        raise
                    else:
                        continue
                if do_print:
                    print("%sDep: %s -> %s" % (" "*depth, dep, self.find_var(dir, dep)))
                try:
                    recdef(dep, depth + 1)
                except RecursionError:
                    # TODO: detect from which var the loop is created move that var
                    raise
        recdef(var)


    def zipdir(self, path, zipname):
        logging.debug("Repacking var...")
        zipf = zipfile.ZipFile(zipname, 'w', zipfile.ZIP_DEFLATED)
        # ziph is zipfile handle
        for root, dirs, files in os.walk(path):
            for file in files:
                zipf.write(os.path.join(root, file), 
                        os.path.relpath(os.path.join(root, file), 
                                        os.path.join(path, '.')))
        zipf.close()
