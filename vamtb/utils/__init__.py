import json
import re
import os
import zipfile
import binascii
import sys
import errno
import ctypes
import glob
from functools import wraps
from pathlib import Path
from datetime import datetime
from vamtb.log import *
from vamtb.vamex import *

#  Binary dir
exec_dir = os.path.dirname(os.path.abspath(sys.argv[0]))

# Vamtb binary location (when running in nuitka, this will be inside the archive to get data dir)
file_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

# Constants
C_YAML = os.path.join(exec_dir, "vamtb.yml")
C_DB = os.path.join(exec_dir, "vars.db")
C_DDIR = os.path.join(exec_dir, "graph")
C_TMPDIR = os.path.join(exec_dir, "tmp")
#C_LOG = exec_dir + "/" + "log-vamtb.txt"  # circular dep (util relies on log which can't rely on util)

TPL_BASE = os.path.join(file_path, "tpl")
C_BAD_DIR = "00Dep"
C_NO_LATEST = "00Old"

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


# Vars for new profile
C_REF_VARS = [
    "AcidBubbles.Embody",
    "AcidBubbles.Glance",
    "AcidBubbles.Keybindings",
    "AcidBubbles.Timeline",
    "AcidBubbles.Utilities",
    "AshAuryn.AshAuryn_Breast_Morphs_Re-Release",
    "AshAuryn.AshAuryn's_101_Female_Genitalia_Morphs",
    "AshAuryn.AshAuryn_HappySurprise_Expression_Morph",
    "AshAuryn.AshAuryn_Nervous_Smiles",
    "AshAuryn.AshAuryn_Sexpressions_2_Point_0",
    "AshAuryn.AshAuryn's_Tears_and_Pain_Pack",
    "AshAuryn.Expressions",
    "AshAuryn.Sexpressions",
    "AWWalker.Genital_Multi-Pass",
    "Blazedust.SessionPlugin_CUAManager",
    "CheesyFX.ShakeIt",
    "Community.PosePack",
    "DoesNotCat.RealFakeLabias",
    "Do_Not_Distribute.Import_Reloaded_Full_Addon",
    "dub.AudioMate",
    "Chokaphi.DecalMaker",
    "ClockwiseSilver.SilverExpressionTool",
    "dreamdealer.lipsync",
    "everlaster.BootyMagic",
    "everlaster.FloatParamRandomizerEE",
    "everlaster.Lumination",
    "everlaster.Naturalis.19",
    "everlaster.RenVR_Originals_Bonus",
    "everlaster.RenVR_Originals_Pack1",
    "everlaster.RenVR_Originals_Pack2",
    "everlaster.RenVR_Originals_Pack3",
    "everlaster.VarLicenseFilter",
    "everlaster.TittyMagic",
    "hazmhox.fluids101",
    "hazmhox.vamatmosphere",
    "hazmhox.vammoan",
    "hazmhox.vamoverlays",
    "hazmhox.vamtweaks",
    "imakeboobies.IKCUA",
    "JaxZoa.SimpleKeybindActions",
    "JayJayWon.ActionGrouper",
    "JayJayWon.ActRandomizer",
    "JayJayWon.BrowserAssist",
    "JayJayWon.UIAssist(Patron)",
    "JayJayWon.VUML",
    "ky1001.AppearanceLoader",
    "ky1001.HandMorphManager",
    "ky1001.HeadLightLink",
    "ky1001.L-R_Swap",
    "ky1001.PoseLoader",
    "LFE.ExtraAutoGenitals0",
    "MeshedVR.3PointLightSetup",
    "MacGruber.Life",
    "MacGruber.Essentials",
    "MeshedVR.PresetsPack",
    "MonsterShinkai.AnusDecals",
    "n00rp.Lighting_Rigs",
    "ParticlePinnacle.ppthighcompressorandvibrations",
    "PluginIdea.ContexMenuSystem(Free)",
    "PluginIdea.GizmosSystem",
    "PluginIdea.MouseWheelToSlider",
    "PluginIdea.MouseWheelToTabChange",
    "PluginIdea.VamInputServer",
    "prestigitis.script-HeelAdjust",
    "ProjectCanyon.MorphMerger",
    "Redeyes.DiviningForeskin.9",
    "Redeyes.DiviningLipsAndHands",
    "Redeyes.GiveMeFPS",
    "Ruvik.PosingHelper",
    "SPQR.ExtraTriggers",
    "SPQR.Fraemework",
    "SPQR.Footsteps",
    "SPQR.MagicAtoms",
    "SPQR.SPQRPerformance",
    "ThatsLewd.CharacterStateManager",
    "ThatsLewd.ExcitementMeter",
    "ToumeiHitsuji.DiviningRod",
    "ToumeiHitsuji.SlapStuff",
    "ToumeiHitsuji.SlapStuffAudioPack",
    "VamTimbo.Extraltodeus-ExpressionRND",
    "Venkman.SceneNinja",
    "via5.AlternateUI",
    "via5.Cue",
    "Vinput.AutoThruster",
    "VRAdultFun.E-motion",
    "WeebU.My_morphs",
    "WrongTamago.WardrobeClothingPresetsPack1",
    "WrongTamago.WardrobeClothingPresetsPack2",
    "WrongTamago.WardrobeClothingPresetsPack3"
    ]

C_NEXT_CREATOR = 127
C_DOT = "c:\\Graphviz\\bin\\dot.exe"
C_MAX_FILES = 50
C_MAX_SIZE = 20 * 1024 * 1024
CR = "\n"

IA_MEDIATYPE = "data"
IA_COLL = "opensource_media"
IA_BASETAGS = [ "virtamate" ]
IA_IDENTIFIER_PREFIX = "vam1__"


def files_in_dir(folder):
    try:
        # Get list of files in folder
        file_list = os.listdir(folder)
    except:
        file_list = []

    fnames = [
        f
        for f in file_list
        if os.path.isfile(os.path.join(folder, f))
        and f.lower().endswith((".var"))
    ]
    return fnames

def prettyjson(obj):
    return json.dumps(obj, indent = 4)

def search_files_indir(fpath, pattern, ign = False):
    return search_files_indir2(fpath, pattern, ign)

def search_files_indir2(fpath, pattern, ign = False, recurse = False):
    pattern = pattern.replace("%", ".*")
    repat = re.compile(fr"{pattern}", flags=re.IGNORECASE)
    res = []
    debug(f"Searching for {pattern} in {fpath}")
    if ign and not os.path.exists(fpath):
        return res
    for thing in os.scandir(fpath):
        if thing.is_file() and repat.match(thing.name):
            res.append(Path(thing))
        if recurse and thing.is_dir():
            res.extend(search_files_indir2(thing.path, pattern, ign, recurse))
    if not ign and not res:
        warn(f"No files found matching pattern {pattern}")
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
        return f"{val}B"

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
    if id == "UserLUT":
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

def get_filepattern_old(ctx):
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

def get_filepattern(ctx):
    file = ctx.obj['file']
    if file:
        if "%" in file:
            pattern = file.replace("%", ".*")
        else:
            pattern = file
        if not pattern.endswith(".var"):
            pattern = pattern + "\.var"
    else:
        pattern = ".*\.var"
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
        except NoMetaJson as e:
            error(f"Var doesnt have meta.json :{e}")

    return wrapper

def del_empty_dirs(target_path):
    for p in Path(target_path).glob('**/*'):
        if p.is_dir() and len(list(p.iterdir())) == 0:
            try:
                os.removedirs(p)
            except:
                pass

def ia_identifier(s:str, prefix=IA_IDENTIFIER_PREFIX )->str:
    return prefix + re.sub('[^0-9a-zA-Z\._\-]+', '_', s)

def get_license_url(s):
    license_url = {
        "CC BY": "https://creativecommons.org/licenses/by/4.0/",
        "CC BY-NC": "https://creativecommons.org/licenses/by-nc/4.0",
        "CC BY-NC-ND": "https://creativecommons.org/licenses/by-nc-nd/4.0",
        "CC BY-ND": "https://creativecommons.org/licenses/by-nd/4.0",
        "CC BY-SA": "https://creativecommons.org/licenses/by-sa/4.0",
        "CC BY-NC-SA" : "http://creativecommons.org/licenses/by-nc-sa/4.0/",
        }

    return license_url.get(s, "")

def xlink(mpath, mdst):
    """Link mdst into mpath"""
    fbase = os.path.basename(mdst)
    debug(f"os.symlink({mdst}, {mpath}/{fbase})")
    os.symlink(f"{mdst}", f"{mpath}/{fbase}", target_is_directory=os.path.isdir(mdst))

def linkdir(dirsrc, dst):
    for f in glob.glob(f"{dirsrc}/*", recursive=True):
        if os.path.islink(f"{dst}/{os.path.basename(f)}"):
            print(f"Removing  : {f}")
            os.unlink(f"{dst}/{os.path.basename(f)}")
        print(f"Linking   : {f} --> {dst}")
        try:
            xlink(dst,f)
        except OSError as e:
            # TODO Remove prefs.json if target exists
            #print(e.errno)
            if e.errno == errno.EINVAL:
                try:
                    isadmin = os.getuid() == 0
                except AttributeError:
                    isadmin = ctypes.windll.shell32.IsUserAnAdmin() != 0
                if not isadmin:
                    critical("You need to run as admin to make links")

def replace_json(fname, key, newvalue):
    with open(fname, 'r') as file:
        json_data = json.load(file)
    json_data[key] = newvalue
    with open(fname, 'w') as file:
        json.dump(json_data, file, indent=2)

def dep_fromjson(json_file, json_content = None, Full=False):

    def _decode_dict(a_dict):
        for id, ref in a_dict.items():  # pylint: disable=unused-variable
#            if id in ['id', 'uid', "url"]:
            if type(ref) == str:
                if ref.startswith("SELF:"):
                    deps['self'].append(ref)
                elif ":" in ref[1:]:
                    name = ref.split(':')[0]
                    ndot = len(name.split('.'))
                    if ndot == 3:
                        deps['var'].append(ref)
                elif any(ref.endswith(s) for s in ['.vmi', ".vam", ".vap", ".json"]):
                    deps['embed'].append(ref)

    deps = { 'embed': [], 'var': [] , 'self': [] }
    if json_file:
        with open(json_file, "r", encoding='utf-8') as fn:
            json.load(fn, object_hook=_decode_dict)
    elif json_content:
        json.loads(json_content, object_hook=_decode_dict)

    return deps