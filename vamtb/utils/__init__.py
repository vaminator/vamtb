#from colorama import Fore, Back, Style, init
from vamtb import vamex
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from zipfile import ZipFile
import colorama
import time
import json
import os
import re
import logging
import binascii

# Conf
C_YAML = "vamtb.yml"

# Types
T_UNK= 0
T_SCENE = 1<<1
T_PERSON = 1<<2
T_HAIR = 1<<3
T_CLOTH = 1<<4
T_POSE = 1<<5
T_MORPH = 1<<6

T_HAIRP = 1<<7
T_CLOTHP = 1<<8
T_POSEP = 1<<9
T_MORPHP = 1<<10

T_ASSET = 1<<11
T_SCRIPT = 1<<12

T_VAC = 1<<13

T_MALE = 1<<14
T_FEMALE = 1<<15

T_JPG = 1<<16

T_VAP = 1<<17  # for now, any preset is a VAP

T_DIR = 1<<18


class __Color:
    __instance = None
    
    def __init__(self):
        logging.debug("Color class initialized")
    
    def col_clear(self):
        return colorama.Style.RESET_ALL

    def dec_cl(func):
        def inner(self, msg):
            return func(self, msg) + self.col_clear()
        return inner

    @dec_cl
    def redf(self, msg):
        return colorama.Fore.RED + msg

    @dec_cl
    def greenf(self, msg):
        return colorama.Fore.GREEN + msg

class CustomFormatter(logging.Formatter):

    blue        = colorama.Fore.BLUE
    yellow      = colorama.Fore.YELLOW
    cyan        = colorama.Fore.CYAN
    green       = colorama.Fore.GREEN
    red         = colorama.Fore.LIGHTRED_EX
    bold_red    = colorama.Fore.RED
    reset       = colorama.Style.RESET_ALL

#    format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"
    format = "%(levelname)8s : %(message)s"

    FORMATS = {
        logging.DEBUG: blue + format + reset,
        logging.INFO: green + format + reset,
        logging.WARNING: cyan + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

class __Log():
   
    def __init__(self):
        self.__ch = None
        self.__fh = None
        self.__logger = self.init_logging()

    def init_logging(self):
        logger = logging.getLogger("vamtb")
        logger.setLevel(logging.DEBUG)
        
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        self.__fh = logging.FileHandler('log-vamtb.txt', mode="w")
        self.__fh.setFormatter(formatter)
        self.__fh.setLevel(logging.DEBUG)
        logger.addHandler(self.__fh)

        self.__ch = logging.StreamHandler()
        self.__ch.setFormatter(CustomFormatter())
        self.__ch.setLevel(logging.WARNING)
        logger.addHandler(self.__ch)

        logger.propagate = False

        return logger

    def toLevel(self, level):
        levels = {
            "WARNING": logging.WARNING,
            "INFO": logging.INFO,
            "DEBUG": logging.DEBUG
        }
        if level in levels.values():
            pass
        elif level in levels:
            level = levels[level]
        elif 0 <= level <= 2:
            level = levels[{0: "WARNING", 1: "INFO", 2: "DEBUG"}[level]]
        else:
            print(f"Can set log level to {level}")
            exit(0)
        return level

    def setLevel(self,level):
        self.__ch.setLevel(self.toLevel(level))

    def critical(self, message):
        self.__logger.critical(message)

    def error(self, message):
        self.__logger.error(message)

    def warn(self, message):
        self.__logger.warn(message)

    def info(self, message):
        self.__logger.info(message)

    def debug(self, message):
        self.__logger.debug(message)


def prettyjson(obj):
    return json.dumps(obj, indent = 4)

def scantree(path):
    for entry in os.scandir(path):
        if entry.is_dir(follow_symlinks=False):
            yield from scantree(entry.path)
        else:
            yield entry

def search_files_indir(fpath, pattern):
    pattern = re.sub(r'([\[\]])','[\\1]',pattern)
    return [ x for x in Path(fpath).glob(f"**/{pattern}") if x.is_file() ]

def getdir(ctx):
    mdir = ctx.obj['dir']
    if not mdir: 
        mdir = os.getcwd()
    if not mdir.endswith("AddonPackages"):
        mdir = f"{mdir}\\AddonPackages"
    if not os.path.isdir(mdir):
        raise vamex.BaseDirNotFound()
    return mdir

def gen_meta(self, **kwargs):
    file_loader = FileSystemLoader('vamtb/tpl')
    env = Environment(loader=file_loader)
    template = env.get_template('meta.json.j2')

    output = template.render(**kwargs)
    return output

def make_var(self, in_dir, in_zipfile, creatorName=None, packageName=None, packageVersion=None, outdir="newvar"):
    """
    Pass a directory or a zipfile and generate var in outdir

    # Todo multiple first dir: Custom/ , Saves/ : set PreloadMorph to true

    """
    tempzipdir="temp"

    # Create input dir if input is a zip
    input_dir = None
    if in_zipfile:
        Path(tempzipdir).mkdir(parents=True, exist_ok=True)
        with ZipFile(in_zipfile, 'r') as customzip:
            customzip.extractall(path=tempzipdir)
        input_dir = tempzipdir
        # We assume for now that the zipfile has a root named Custom
    else: 
        # We have directory containing a creator content
        input_dir = in_dir

    assert(input_dir is not None)

    logging.debug(f"Input is {input_dir}")

    # Detect properties
    # Or ask
    if not creatorName:
        creatorName = input("Give creator name:")
    if not packageName:
        packageName = input("Give package name:")
    if not packageVersion:
        while True:
            try:
                packageVersion = input("Give package version[1]:")
                if not packageVersion:
                    packageVersion = 1
                packageVersion = int(packageVersion)
            except:
                print("Noo, I need an integer")
            else:
                break

    # Directory structure check
    for p in Path(input_dir).glob('**/*'):
        if p.is_dir():
            rp = Path(os.path.relpath(p, input_dir))
            if len(rp.parts)>1 and rp.parts[0] == "Saves" and (rp.parts[1] != "scene" and rp.parts[1] !="Person"):
                logging.error(f"Path {p} is not legal")
                ok = input("Abort? Hit simply Enter:")
                if not ok:
                    raise vamex.IllegalPath

    _ = input(f"Last chance to copy/move files inside {Path(input_dir).resolve()}. Hit enter when ready to proceed:")

    # Detect content
    is_scene = False
    if Path(input_dir,"Saves/scene").is_dir():
        is_scene = True

    # List only "content"
    contents = [ Path(os.path.relpath(x, input_dir)) for x in Path(input_dir).glob('**/*') if x.is_file() and x.name!="meta.json" ]
    contentsp = [ f.as_posix() for f in contents ]
    logging.debug(f"Found {len(contentsp)} elements in {input_dir}")    

    # List referenced dependencies
    all_deps = []
    if is_scene:
        for scene in [ p for p in Path(input_dir, "Saves/scene").glob('**/*') if p.is_file() and p.suffix == ".json" and p.name != "meta.json" ]:
            logging.debug(f"Detected scene {scene}, searching referenced dependencies")
            deps = self.dep_fromjson(json_file=scene)
            varnames = list(set([ v.split(':')[0] for v in deps['var'] ]))
            all_deps.extend(varnames)

    logging.info(f"Found deps:{all_deps}")
    # Filter stuffs
    # TODO
    repack_reref_dir(input_dir)

    # Detect creator(s)
    dcreators = get_creators_dir(input_dir)
    ncreator = dcreators[0] if dcreators else 0
    if len(dcreators) and ncreator != creatorName:
        logging.error(f"From files, creator(s) found: { ','.join(dcreators) }")
        creatorName = input(f"Set creator from {creatorName} to {ncreator} or set manually:")
        if not creatorName:
            creatorName = ncreator
            logging.debug(f"Setting creator to {creatorName}")

    logging.debug("Generating meta.json")
    meta_json = gen_meta(creatorName=creatorName, packageName=packageName, contents=contentsp, deps=all_deps, promotionalLink=datetime.now(timezone.utc))
    with open(f"{input_dir}/meta.json", "w") as meta_file: 
        meta_file.write(meta_json) 

    # We want files inside outdir
    finalVar = f"{creatorName}.{packageName}.{packageVersion}"    
    logging.debug(f"Packing var file {finalVar}")
    with ZipFile(f'{finalVar}.var', 'w') as myzip:
        for file in Path(input_dir).glob('**/*'):
            myzip.write(filename = file, arcname = os.path.relpath(file, input_dir))

    # Remove tempdir and outdir
    if in_zipfile:
        shutil.rmtree(tempzipdir)

def repack_reref(self, mfile):
    orig = mfile.with_suffix(f"{mfile.suffix}.orig")
    mfile.rename(orig)
    with open(mfile, "w", encoding='utf-8') as dest:
        with open(orig, "r", encoding='utf-8') as src:
            for l in src:
                if '"Custom/' in l:
                    ol = l
                    l = ol.replace('Custom', 'SELF:/Custom', 1)
                    logging.debug(f"{mfile}: rerefed {ol} to {l}")
                dest.write(l)
    orig.unlink()


def repack_reref_dir(self, input_dir):
    for f in Path(input_dir).glob('**/*'):
        if f.suffix in ['.vap', '.vaj', '.json']:
            repack_reref(f)

def get_creators_dir(self, input_dir):
    lc = set()
    for fn in Path(input_dir).glob('**/*'):
        if fn.suffix in ['.vam']:
            with open(fn, "r", encoding='utf-8') as f:
                content = json.load(f)
                if "creatorName" in content:
                    lc.add(content['creatorName'])
    return list(lc)

def get_type(self, infile):
    """
    From a file, detect resource type
    """
    infile = Path(infile)
    if infile.is_dir():
        return T_DIR
    suffix = infile.suffix
    if suffix == ".assetbundle" or suffix == ".scene":
        return T_ASSET
    if suffix == ".cs":
        return T_SCRIPT
    if suffix == ".json":
        with open(infile, "rt", encoding='utf-8') as f:
            js = json.load(f)
            if "playerHeightAdjust" in js:
                return T_SCENE
            else:
                return T_POSE
    if suffix == ".vmi" or suffix == ".vmb":
        return T_MORPH
    if suffix == ".vam":
        with open(infile, "rt", encoding='utf-8') as f:
            js = json.load(f)
            if js['itemType'] == "ClothingFemale":
                return T_CLOTH | T_FEMALE
            if js['itemType'] == "ClothingMale":
                return T_CLOTH | T_MALE
            if js['itemType'] == "HairFemale":
                return T_HAIR | T_FEMALE
            if js['itemType'] == "HairMale":
                return T_HAIR | T_MALE
    if suffix == ".vaj" or suffix == ".vab":
        return get_type(infile.with_suffix(".vam"))
    if suffix == ".vap":
        logging.warning("Didn't detect type of VAP")
        return T_VAP
    if suffix == ".jpg":
        logging.warning("Didn't detect type of JPG")
        return T_JPG
    
    return T_UNK

def remove_empty_folders(path_abs):
    walk = list(os.walk(path_abs))
    for path, _, _ in walk[::-1]:
        if len(os.listdir(path)) == 0:
            os.remove(path)

def get_reqfile(self, infile, mtype):
    infile=Path(infile)
    basedir=infile.parent
    req = set()
    req.add(infile)
    logging.debug(f"Search for associated files for {infile}")
    pic = list(Path(basedir).glob(f"**/{infile.with_suffix('.jpg').name}"))
    if pic and pic[0].is_file():
        req.add(pic[0])
    if mtype == T_ASSET or mtype == T_SCRIPT:
        pass
    elif mtype == T_SCENE or mtype == T_POSE:
        pass
    elif mtype & T_MORPH:
        vmi = list(Path(basedir).glob(f"**/{infile.with_suffix('.vmi').name}"))[0]
        vmb = list(Path(basedir).glob(f"**/{infile.with_suffix('.vmb').name}"))[0]
        if vmi.is_file() and vmb.is_file():
            req.add(vmi)
            req.add(vmb)
        else:
            logging.error(f"Missing files for {infile}")
            raise vamex.MissingFiles
    elif mtype & T_CLOTH or mtype & T_HAIR:
        vam = list(Path(basedir).glob(f"**/{infile.with_suffix('.vam').name}"))[0]
        vaj = list(Path(basedir).glob(f"**/{infile.with_suffix('.vaj').name}"))[0]
        vab = list(Path(basedir).glob(f"**/{infile.with_suffix('.vab').name}"))[0]
        if vam.is_file() and vaj.is_file() and vab.is_file():
            req.add(vam)
            req.add(vaj)
            req.add(vab)
        else:
            logging.error(f"Missing files for {infile}")
            raise vamex.MissingFiles
    elif mtype == T_JPG or mtype == T_VAP:
        pass
    else:
        logging.error(f"Can't detect required files for {infile} of type {mtype}")
        raise vamex.UnknownContent

    return list(req)


def crc32c(content):
    buf = (binascii.crc32(content) & 0xFFFFFFFF)
    return "%08X" % buf

def clean_dir_safe(path):
    """
    So you can't safely remove a file because explorer is accessing it.
    """
    def onerror(function, path, exc_info):
        # Handle ENOTEMPTY for rmdir
        if (function is os.rmdir
            and issubclass(exc_info[0], OSError)
            and exc_info[1].errno == errno.ENOTEMPTY):
            timeout = 0.001
            while timeout < 2:
                if not os.listdir(path):
                    return os.rmdir(path)
                time.sleep(timeout)
                timeout *= 2
        raise

    try:
        shutil.rmtree(path, onerror=onerror)
    except FileNotFoundError:
        pass
    # rmtree didn't fail, but path may still be linked if there is or was
    # a handle that shares delete access. Assume the owner of the handle
    # is watching for changes and will close it ASAP. So retry creating
    # the directory by using a loop with an increasing timeout.
    timeout = 0.001
    while True:
        try:
            return os.mkdir(path)
        except PermissionError as e:
            # Getting access denied (5) when trying to create a file or
            # directory means either the caller lacks access to the
            # parent directory or that a file or directory with that
            # name exists but is in the deleted state. Handle both cases
            # the same way. Otherwise, re-raise the exception for other
            # permission errors, such as a sharing violation (32).
            if e.winerror != 5 or timeout >= 2:
                raise
            time.sleep(timeout)
            timeout *= 2

def log_setlevel(level):
    __log.setLevel(level)

def info(message):
    __log.info(message)

def error(message):
    __log.error(message)

def warn(message):
    __log.warn(message)

def critical(message, doexit=False):
    __log.critical(message)
    if doexit:
        exit(0)

def debug(message):
    __log.debug(message)

def green(message):
    return __col.greenf(message)

def red(message):
    return __col.redf(message)

# GLobal objects as singletons
__col = __Color()
__log = __Log()

