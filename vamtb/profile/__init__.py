from pathlib import Path
import shutil

from vamtb.vamex import *
from vamtb.utils import *
from vamtb.log import *
from vamtb.var import Var

dirs = ("AddonPackages", "Assets", "Custom", "Saves", "Custom/SubScene")
files = ("prefs.json",)

ddir = None
def linkfile2ddir(mvar):
    global ddir

    srcfile = mvar.path
    xlink(ddir, srcfile)
    print(f">> Linked dependency {srcfile}")

class ProfileMgr:

    def __init__(self, multidir, exedir, cachedir, vardir, refvars):
        """
        """
        # Profile name
        self.__np = None

        multidir or critical("Need a profile base directory")
    
        if Path(multidir).is_dir():
            self.__bsrc = multidir
            # FIXME
            # Why link to Full being a link to vars
            # Now used for Custom/ and Saves/
            # But not used for ref vars
            self.__basedir = multidir + "/" + "Full"
        else:
            critical(f"{multidir} is not a directory, please create it manually!")
    
        # Path where vars are
        # We can't use exedir/AddonPackages as its a link to current profile
        if Path(vardir).is_dir():
            self.__vardir = vardir
        else:
            critical(f"{vardir} should hold your vars, but doesn't exists!")

        if Path(exedir, "VaM.exe").is_file():
            self.__dst = exedir
        else:
            critical(f"{exedir}/VaM.exe not found!")

        if Path(cachedir).is_dir():
            self.__cachedir = cachedir
        else:
            critical(f"{cachedir} is not a directory, please create it manually!")

        self.__refvars = refvars

    # Profile root directory (multidir/<profilename>)
    @property
    def __base(self):
        return f"{self.__bsrc}/{self.__np}"

    def new(self, profileName=None):
        global ddir

        if not profileName:
            self.__np = input("Name of new profile: ")
        else:
            self.__np = profileName
        try:
            os.mkdir(self.__base)
        except FileExistsError:
            print(f"Directory {self.__base} exists")

        exists = any(os.path.isdir(f"{self.__base}/{e}") for e in dirs) or \
            any(os.path.isfile(f"{self.__base}/{e}") for e in files)
        noexists = all(os.path.isdir(f"{self.__base}/{e}") for e in dirs) and \
            all(os.path.isfile(f"{self.__base}/{e}") for e in files)

        if exists and not noexists:
            print("Some files or directory exists but not all, only nonexisting will be replaced")

        # Create empty directories
        # If Profile is "Full", we want AddonPackages being a link to exedir/AddonPackages        
        for d in dirs:
            try:
                if self.__np == "Full" and d == "AddonPackages":
                    if Path(self.__base, d).exists():
                        if not Path(self.__base, d).is_symlink():
                            critical(f"{self.__base}/{d} should be a link to {self.__exedir}/{d}, Please remove that dir.")
                    else:
                        xlink( f"{self.__base}/AddonPackages/", f"{self.__dst}/AddonPackages/" )
                        print(f"Linked {self.__base}/AddonPackages/ to {self.__dst}/AddonPackages/")
                else:
                    os.mkdir(f"{self.__base}/{d}")
                    print(f"Created dir {self.__base}/{d}")
            except FileExistsError:
                pass

        # Copy some ref files from 
        for i, f in enumerate(files):
            if not os.path.isfile(f"{self.__base}/{f}"):
                shutil.copy2( os.path.join(self.__dst, files[i]), f"{self.__base}/{f}")
                if files[i] == "prefs.json":
                    replace_json(f"{self.__base}/{f}", "cacheFolder", self.__cachedir + "\\" + f"vam_cache_{self.__np}")

        # If we are in Full profile, these should be existing directories
        for mdir in ("PluginPresets", ):
            if self.__np == "Full":
                os.mkdir(f"{self.__base}/Custom/{mdir}")
            else:
                try:
                    xlink( f"{self.__base}/Custom/", f"{self.__basedir}/Custom/{mdir}" )
                except OSError:
                    pass

        #TODO clarify
        for mdir in ("Anonymous", ):
            if self.__np == "Full":
                os.mkdir(f"{self.__base}/Custom/SubScene/{mdir}")
            else:
                try:
                    xlink( f"{self.__base}/Custom/SubScene", f"{self.__basedir}/Custom/SubScene/{mdir}" )
                except OSError:
                    pass

        for mdir in ("PluginData", ):
            if self.__np == "Full":
                os.mkdir(f"{self.__base}/Saves/{mdir}")
            else:
                try:
                    xlink( f"{self.__base}/Saves/", f"{self.__basedir}/Saves/{mdir}" )
                except OSError:
                    pass
    
        # Now link ref vars unlesss we are in Profile Full
        if self.__np != "Full":
            for refvar in self.__refvars:
                debug(f"Refvar {refvar}")
                version = None
                try:
                    creator, asset, version = refvar.split('.', 3)
                except ValueError:
                    creator, asset = refvar.split('.', 2)
                if not version:
                    ln = f"{creator}.{asset}.latest"
                else:
                    ln = f"{creator}.{asset}.{version}"
                debug(f"Searching for {ln}")
                try:
                    with Var(ln, self.__vardir, use_db=True) as mvar:
                        refvarpath = mvar.path
                        debug(f"Linking  {refvarpath} to {self.__base}/AddonPackages")
                        try:
                            ddir = f"{self.__base}/AddonPackages"
                            try:
                                xlink( ddir, refvarpath )
                                print(f">Linked  {refvarpath} to {self.__base}/AddonPackages")
                            except OSError:
                                pass
                        except OSError:
                            # Already linked but keep on going for dependencies
                            pass
                except VarNotFound:
                    warn(f"We did not find {refvar} to link")
                    continue
                try:
                    with Var(refvarpath, self.__vardir, use_db=True) as mlatest:
                        debug(f"Searching dep of {mlatest.var}")
                        mlatest.rec_dep(stop=False, dir=self.__vardir, func=linkfile2ddir)
                except OSError:
                    pass

    def select(self, profilename):
        self.__np = profilename
        print(f"Selecting {self.__np}")
        linkdir(self.__base, self.__dst)
