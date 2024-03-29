from pathlib import Path
import shutil

from vamtb.vamex import *
from vamtb.utils import *
from vamtb.log import *
from vamtb.var import Var
import errno

dirs = ("AddonPackages", "Assets", "Custom", "Saves", "Custom/SubScene")
files = ("prefs.json",)

ddir = None
def linkfile2ddir(mvar):
    global ddir

    srcfile = mvar.path
    try:
        xlink(ddir, srcfile)
        print(f">> Linked dependency {srcfile} to {ddir}")
    except OSError as e:
        if e.errno == errno.EEXIST :
            pass
        else:
            raise

class ProfileMgr:

    # Profile name
    __np = None
    # Base multidir (under which profiles are)
    __bsrc = None
    # Directory where Full profile is (__bsrc/Full)
    __basedir = None
    # Directory where vars are
    __vardir = None
    # Directory where vam.exe is
    __dst = None

    def __init__(self, multidir, exedir, cachedir, vardir, refvars=None):

        multidir or critical("Need a profile base directory")
    
        if Path(multidir).is_dir():
            ProfileMgr.__bsrc = multidir
            # For Full profile, Addonpackages directory is a link to var pool Addonpackages *directory*
            # For other profiles, vars inside Addonpackages are links to var *files* inside pool AddonPackages directory.
            # Custom/ and Saves/ will link to Full profile directories (shared preferences for Session Plugins, Assets, SubScenes, ..)
            ProfileMgr.__basedir = multidir + "/" + "Full"
        else:
            critical(f"{multidir} is not a directory, please create it manually!")
    
        # Var pool
        # Trap: We can't use exedir/AddonPackages as its a link to current profile
        if Path(vardir).is_dir():
            ProfileMgr.__vardir = vardir
        else:
            critical(f"{vardir} should hold your vars, but doesn't exists!")

        if Path(exedir, "VaM.exe").is_file():
            ProfileMgr.__dst = exedir
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
        return f"{ProfileMgr.__bsrc}/{ProfileMgr.__np}"

    def new(self, profileName=None):
        global ddir

        if not profileName:
            ProfileMgr.__np = input("Name of new profile: ")
        else:
            ProfileMgr.__np = profileName
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
        # If Profile is "Full", we want AddonPackages being a link to Pool/AddonPackages        
        for d in dirs:
            try:
                if ProfileMgr.__np == "Full" and d == "AddonPackages":
                    if Path(self.__base, d).exists():
                        if not Path(self.__base, d).is_symlink():
                            critical(f"{self.__base}/{d} should be a link to {self.__vardir}/{d}, Please remove that dir.")
                    else:
                        xlink( f"{self.__base}", f"{ProfileMgr.__vardir}" )
                        print(f"Linked {self.__base}/AddonPackages/ to {ProfileMgr.__vardir}")
                else:
                    os.mkdir(f"{self.__base}/{d}")
                    print(f"Created dir {self.__base}/{d}")
            except FileExistsError:
                pass

        # Copy some ref files from 
        for i, f in enumerate(files):
            if not os.path.isfile(f"{self.__base}/{f}"):
                shutil.copy2( os.path.join(ProfileMgr.__dst, files[i]), f"{self.__base}/{f}")
                if files[i] == "prefs.json":
                    replace_json(f"{self.__base}/{f}", "cacheFolder", self.__cachedir + "\\" + f"vam_cache_{ProfileMgr.__np}")

        # If we intiate the Full profile, these should be existing directories
        for mdir in ("PluginPresets", ):
            if ProfileMgr.__np == "Full":
                os.mkdir(f"{self.__base}/Custom/{mdir}")
            else:
                try:
                    xlink( f"{self.__base}/Custom/", f"{ProfileMgr.__basedir}/Custom/{mdir}" )
                except OSError as e:
                    if e.errno == errno.EEXIST :
                        pass

        # SubScenes/Anonymous is a link to allow sharing subscenes
        for mdir in ("Anonymous", ):
            if ProfileMgr.__np == "Full":
                os.mkdir(f"{self.__base}/Custom/SubScene/{mdir}")
            else:
                try:
                    xlink( f"{self.__base}/Custom/SubScene", f"{ProfileMgr.__basedir}/Custom/SubScene/{mdir}" )
                except OSError as e:
                    if e.errno == errno.EEXIST :
                        pass

        # Share pluginData.
        for mdir in ("PluginData", ):
            if ProfileMgr.__np == "Full":
                os.mkdir(f"{self.__base}/Saves/{mdir}")
            else:
                try:
                    xlink( f"{self.__base}/Saves/", f"{ProfileMgr.__basedir}/Saves/{mdir}" )
                except OSError as e:
                    if e.errno == errno.EEXIST :
                        pass
    
        # Now link ref vars unlesss we are in Profile Full
        if ProfileMgr.__np != "Full":
            if self.__refvars and input(f"Add your {len(self.__refvars)} reference vars [Y]N ?:").upper != "N":
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
                        with Var(ln, ProfileMgr.__vardir, use_db=True, localdir=False) as mvar:
                            refvarpath = mvar.path
                            debug(f"Linking  {refvarpath} to {self.__base}/AddonPackages")
                            ddir = f"{self.__base}/AddonPackages"
                            try:
                                xlink( ddir, refvarpath )
                                print(f">Linked {refvarpath} to {self.__base}/AddonPackages")
                            except OSError as e:
                                if e.errno == errno.EEXIST :
                                    # Already linked but keep on going for dependencies
                                    pass
                    except VarNotFound:
                        warn(f"We did not find {refvar} to link")
                        continue
                    # Localdir set to false because we only want to search in __AddonPackages and not in current directory
                    # In case vtb profile is run in a directory where a dependency file exists
                    with Var(refvarpath, ProfileMgr.__vardir, use_db=True, localdir=False) as mlatest:
                        debug(f"Searching dep of {mlatest.var}")
                        mlatest.rec_dep(stop=False, dir=ProfileMgr.__vardir, func=linkfile2ddir)

    def select(self, profilename):
        ProfileMgr.__np = profilename
        print(f"Selecting {ProfileMgr.__np}")
        linkdir(self.__base, ProfileMgr.__dst)
        self.verify()
        print(red("///// WARNING \\\\\\\\\\"))
        print(red("Do not erase on disk the currently selected profile or you will loose original files (restore from trashbin)"))
        print(red("///// WARNING \\\\\\\\\\"))

    def list(self):
        adirs = next(os.walk(ProfileMgr.__bsrc))[1]
        return adirs
    
    def verify(self):
        info("Verifying dead links...")
        addon = os.path.join(ProfileMgr.__dst, "AddonPackages")
        try:
            mfiles = search_files_indir2(addon, "%")
        except OSError as e:
            critical(f"You have a broken link {e}")
        info("Looks good")
            
    def current(self):
        addon = os.path.join(ProfileMgr.__dst, "AddonPackages")
        if os.path.islink(addon):
            daddon = os.path.realpath(addon)
            return os.path.basename(os.path.dirname(daddon))
        else:
            return None
