from vamtb import vamex
from zipfile import ZipFile
import os
import shutil
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from vamtb.log import *
from vamtb.utils import *
from datetime import datetime, timezone

"""
Old code
"""


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

def prep_tree(file, dir, creator, do_move = False):

    # Get type
    mtype = get_type(file)
    debug(f"Detected file {file} as type {mtype}")

    if mtype == T_DIR:
        # Copy subtree relative to a root (asked to user)
        parents = [ Path(file) ] 
        for p in Path(file).parents:
            parents.append(p)
        for i, p in enumerate(parents, start=1):
            tab='\t'
            print(f"{i}{tab}{p}")
        root = int(input("Select relative root dir:")) - 1
        reldir = parents[root]
        # FIXME this copies all directories at the same level, not only the selected one
        shutil.copytree(reldir, dir, dirs_exist_ok = True)
        if do_move:
            shutil.rmtree(file)
            
        return

    # Require some files
    reqfiles = get_reqfile(file, mtype)
    nl = '\n'
    debug(f"List of files:{nl}{nl.join(list(map(lambda x:x.as_posix(), reqfiles)))}")

    # Create dirstruct
    d = None
    if mtype == T_SCENE:
        d = Path(dir,"Saves", "scene")

    if mtype == T_ASSET:
        d = Path(dir,"Custom", "Assets", creator)

    if mtype & T_CLOTH:
        if mtype & T_FEMALE:
            gend = "Female"
        elif mtype & T_MALE:
            gend = "Male"
        else:
            assert(False)
        d = Path(dir,"Custom", "Clothing", gend, creator)

    if not d:
        listdirs = []
        for p in Path(dir).glob("**/*"):
            if p.is_dir():
                listdirs.append(Path(os.path.relpath(p, dir)))

        for i, ldir in enumerate(listdirs, start=1):
            tab='\t'
            print(f"{i}{tab}{ldir}")
        cd = input("Choose directory to copy that to (or type new dir relative to var root):") 
        try:
            idx = int(i)-1
            d = list(listdirs)[idx]
        except ValueError:
            d = Path(dir, cd).resolve()
        finally:
            d = Path(dir, d)

    debug(f"Puting file in {d.resolve()}")
    d.mkdir(parents=True, exist_ok=True)

    # Copy or Move files
    for f in reqfiles:
        if do_move:
            shutil.move(f"{f}", f"{d}")
        else:
            shutil.copy(f, d)

def gen_meta(**kwargs):
    global TPL_BASE

    file_loader = FileSystemLoader(TPL_BASE)
    env = Environment(loader=file_loader)
    template = env.get_template('meta.json.j2')

    output = template.render(**kwargs)
    return output

def make_var(in_dir, in_zipfile, creatorName=None, packageName=None, packageVersion=None, outdir="newvar"):
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

    debug(f"Input is {input_dir}")

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
            except ValueError:
                print("Noo, I need an integer")
            else:
                break

    # Directory structure check
    for p in Path(input_dir).glob('**/*'):
        if p.is_dir():
            rp = Path(os.path.relpath(p, input_dir))
            if len(rp.parts)>1 and rp.parts[0] == "Saves" and (rp.parts[1] != "scene" and rp.parts[1] !="Person"):
                error(f"Path {p} is not legal")
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
    debug(f"Found {len(contentsp)} elements in {input_dir}")    

    # List referenced dependencies
    all_deps = []
    if is_scene:
        for scene in [ p for p in Path(input_dir, "Saves/scene").glob('**/*') if p.is_file() and p.suffix == ".json" and p.name != "meta.json" ]:
            debug(f"Detected scene {scene}, searching referenced dependencies")
            deps = dep_fromjson(json_file=scene)
            varnames = list(set([ v.split(':')[0] for v in deps['var'] ]))
            all_deps.extend(varnames)

    info(f"Found deps:{all_deps}")
    # 
    # TODO Filter stuffs
    repack_reref_dir(input_dir)

    # Detect creator(s)
    dcreators = get_creators_dir(input_dir)
    ncreator = dcreators[0] if dcreators else 0
    if len(dcreators) and ncreator != creatorName:
        error(f"From files, creator(s) found: { ','.join(dcreators) }")
        creatorName = input(f"Set creator from {creatorName} to {ncreator} or set manually:")
        if not creatorName:
            creatorName = ncreator
            debug(f"Setting creator to {creatorName}")

    debug("Generating meta.json")
    meta_json = gen_meta(creatorName=creatorName, packageName=packageName, contents=contentsp, deps=all_deps, promotionalLink=datetime.now(timezone.utc))
    with open(f"{input_dir}/meta.json", "w") as meta_file: 
        meta_file.write(meta_json) 

    # We want files inside outdir
    finalVar = f"{creatorName}.{packageName}.{packageVersion}"    
    debug(f"Packing var file {finalVar}")
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
                    debug(f"{mfile}: rerefed {ol} to {l}")
                dest.write(l)
    orig.unlink()


def repack_reref_dir(input_dir):
    for f in Path(input_dir).glob('**/*'):
        if f.suffix in ['.vap', '.vaj', '.json']:
            repack_reref(f)

def get_creators_dir(input_dir):
    lc = set()
    for fn in Path(input_dir).glob('**/*'):
        if fn.suffix in ['.vam']:
            with open(fn, "r", encoding='utf-8') as f:
                content = json.load(f)
                if "creatorName" in content:
                    lc.add(content['creatorName'])
    return list(lc)

def get_type(infile):
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
        warning("Didn't detect type of VAP")
        return T_VAP
    if suffix == ".jpg":
        warning("Didn't detect type of JPG")
        return T_JPG
    
    return T_UNK

def remove_empty_folders(path_abs):
    walk = list(os.walk(path_abs))
    for path, _, _ in walk[::-1]:
        if len(os.listdir(path)) == 0:
            os.remove(path)

def get_reqfile(infile, mtype):
    infile=Path(infile)
    basedir=infile.parent
    req = set()
    req.add(infile)
    debug(f"Search for associated files for {infile}")
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
            error(f"Missing files for {infile}")
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
            error(f"Missing files for {infile}")
            raise vamex.MissingFiles
    elif mtype == T_JPG or mtype == T_VAP:
        pass
    else:
        error(f"Can't detect required files for {infile} of type {mtype}")
        raise vamex.UnknownContent

    return list(req)

