'''Var file naming'''
import json
import logging
import os
import shutil
from pathlib import Path
from zipfile import ZipFile, BadZipFile
from jinja2 import Environment, FileSystemLoader
import vamex
import traceback
import piexif
import vamdirs
from PIL import Image
import json

def split_varname(fname, dest_dir):
    if not isinstance(fname, os.PathLike):
        fname = Path(fname)
    creator, _ = fname.name.split('.', 1)
    # fpath = fname.parents[0]    
    newpath = Path("%s/%s"% (dest_dir, creator))
    newname = Path("%s/%s" % (newpath, fname.name))
    if fname == newname:
        return
    try:
        os.makedirs(newpath)
    except FileExistsError:
        pass
    logging.info("Moving %s to %s" % (fname, newname))
    try:
        fname.rename(newname)
    except FileExistsError:
        pass
        try:
            Path.unlink(fname)
        except PermissionError:
            logging.error(f"Couldnt remove {fname}")
            pass

def is_namecorrect(fname, checksuffix=True):
    """ Takes as parameter a var filename with extension """
    logging.debug("Checking var %s" % fname)
    if not isinstance(fname, os.PathLike):
        fname = Path(fname)
    if checksuffix and fname.suffix != ".var":
        raise vamex.VarExtNotCorrect(fname)
    try:
        _, _, _ = fname.with_suffix('').name.split('.')
    except ValueError:
        pass
        raise vamex.VarNameNotCorrect(fname)
    return True

def remove_empty_folders(path_abs):
    walk = list(os.walk(path_abs))
    for path, _, _ in walk[::-1]:
        if len(os.listdir(path)) == 0:
            os.remove(path)

def extract_meta_var(fname):
    """ Extract meta.json and return parsed body from var """
    try:
        with ZipFile(fname, mode='r') as myvar:
            with myvar.open("meta.json") as meta:
                try:
                    return json.load(meta)
                except Exception as e:
                    pass
                    raise vamex.VarMetaJson(f"Failed to decode meta json {fname}: {e}")
    except FileNotFoundError:
        return

def get_exif(fname):
    exif = piexif.load(fname)
    return exif

def test_print_exif(fname):
    exif = get_exif(fname)
    t = exif["0th"][piexif.ImageIFD.XPKeywords]
    convm = bytes(t).decode('utf-16')[:-1]
    tags = convm.split(';')
    return tags

def set_tag(fname, tags):
    logging.debug(f"Setting tag of {fname} to {tags}")
    try:
        exif = get_exif(fname)
        exif["0th"][piexif.ImageIFD.XPKeywords] = f"{';'.join(tags)} ".encode('utf-16')
        try:
            exif_bytes = piexif.dump(exif)
        except piexif._exceptions.InvalidImageDataError:
            logging.warning(f"Image {fname} has incorrect EXIF information")
            del exif["1st"]
            del exif["thumbnail"]
            exif_bytes = piexif.dump(exif)
        img = Image.open(fname)
        img.save(fname, exif=exif_bytes)
    except Exception as e:
        logging.error(f"Couldnt edit tag of jpg {fname}: {e}")

def find_same_jpg(listFiles, name):
    fpath_listfiles = [ Path(f) for f in listFiles ]
    fname = Path(name).with_suffix('').name
    candidates = [ f for f in fpath_listfiles if f.name.lower().endswith(f"{fname.lower()}.jpg") ]
    return candidates

def thumb_var(fname, outdir):
    """ Extract any jpeg to output dir """
    flatdirname="00-Flat"
    save_scene=set()
    save_person=set()
    cloth=set()
    clothp=set()
    morph=set()
    morphp=set()
    asset=set()
    hair=set()
    hairp=set()
    script=set()
#    texture=set() Tricky
    pose=set()
    posep=set()
    appear=set()
    tags=set()
    ref_icon=Path(os.path.dirname(os.path.realpath(__file__)), "..", "gear.jpg").resolve()

    Path(outdir, flatdirname).mkdir(parents=True, exist_ok=True)
    logging.info(f"Searching thumb for {fname}")
    try:
        with ZipFile(fname, mode='r') as myvar:
            listOfFileNames = [f for f in myvar.namelist() if not f.endswith("meta.json") and not f.endswith('/')]
            listOfJpg = [f for f in myvar.namelist() if f.endswith(".jpg")]
            # check save scene
            for f in listOfFileNames:
                if f.endswith(".json") and ("saves/scene" in f.lower() or "saves/scenes" in f.lower() or "save/scene" in f.lower() or "save/scenes" in f.lower()):
                    save_scene.add(f)
                if f.endswith(".json") and ("saves/person" in f.lower() or "saves/persons" in f.lower() or "save/person" in f.lower() or "save/persons" in f.lower()):
                    save_person.add(f)
                if f.endswith(".vam") or f.endswith(".vaj"):
                    if "cloth" in f.lower():
                        cloth.add(f)
                    elif "hair" in f.lower():
                        hair.add(f)
                    else:
                        logging.error(f"Can't detect type {f}")
                        raise vamex.UnknownExtension
                if f.endswith(".vmi"):
                    morph.add(f)
                if f.endswith(".assetbundle"):
                    asset.add(f)
                if f.endswith(".vap"):
                    if "appearance" in f.lower():
                        appear.add(f)
                    elif "morph" in f.lower():
                        morphp.add(f)
                    elif "pose" in f.lower():
                        posep.add(f)
                    elif "hair" in f.lower():
                        hairp.add(f)
                    elif "cloth" in f.lower():
                        clothp.add(f)
                if f.endswith(".cs"):
                    script.add(f)
                if f.endswith(".json") and "pose" in f.lower():
                    pose.add(f)
            logging.debug(f"For {fname} we found:")
            if save_scene:
                logging.debug(f"saved scene: {save_scene}")
            if save_person:
                logging.debug(f"saved person: {save_person}")
            if cloth:
                logging.debug(f"clothes:{cloth}")
            if hair:
                logging.debug(f"hair:{hair}")
            if morph:
                logging.debug(f"morphs:{morph}")
            if asset:
                logging.debug(f"assets: {asset}")
            if clothp:
                logging.debug(f"cloth presets:{clothp}")
            if posep:
                logging.debug(f"pose presets:{posep}")
            if hairp:
                logging.debug(f"hair presets:{hairp}")
            if morphp:
                logging.debug(f"morph preset:{morphp}")
            if script:
                logging.debug(f"scripts:{script}")
            if pose:
                logging.debug(f"pose:{pose}")
            if appear:
                logging.debug(f"appearance:{appear}")

            # Now try to find a jpg
            found = False
            if save_scene:
                first_scene = list(save_scene)[0]
                jpg = find_same_jpg(listOfFileNames, first_scene)
                if not jpg:
                    logging.debug(f"We had a scene {first_scene} but didn't find the same jpg")
                else:
                    logging.debug(f"Found jpg {jpg[0].name}")
                    found = True
                    tags.add("Scene")
            if not found and save_person:
                first_person = list(save_person)[0]
                jpg = find_same_jpg(listOfFileNames, first_person)
                if not jpg:
                    logging.debug(f"We had a person {first_person} but didn't find the same jpg")
                else:
                    logging.debug(f"Found jpg {jpg[0].name}")
                    found = True
                    tags.add("Person")
            if not found and appear:
                first_person = list(appear)[0]
                jpg = find_same_jpg(listOfFileNames, first_person)
                if not jpg:
                    logging.debug(f"We had a person appearance {first_person} but didn't find the same jpg")
                else:
                    logging.debug(f"Found jpg {jpg[0].name}")
                    found = True
                    tags.add("Person")
            if not found and clothp:
                first_clothp = list(clothp)[0]
                jpg = find_same_jpg(listOfFileNames, first_clothp)
                if not jpg:
                    logging.debug(f"We had a cloth preset {first_clothp} but didn't find the same jpg")
                else:
                    logging.debug(f"Found jpg {jpg[0].name}")
                    found = True
                    tags.add("Cloth")
            if not found and hairp:
                first_hairp = list(hairp)[0]
                jpg = find_same_jpg(listOfFileNames, first_hairp)
                if not jpg:
                    logging.debug(f"We had a hair preset {first_hairp} but didn't find the same jpg")
                else:
                    logging.debug(f"Found jpg {jpg[0].name}")
                    found = True
                    tags.add("Hair")
            if not found and morphp:
                first_morphp = list(morphp)[0]
                jpg = find_same_jpg(listOfFileNames, first_morphp)
                if not jpg:
                    logging.debug(f"We had a morph preset {first_morphp} but didn't find the same jpg")
                else:
                    logging.debug(f"Found jpg {jpg[0].name}")
                    found = True
                    tags.add("Morph")
            if not found and posep:
                first_posep = list(posep)[0]
                jpg = find_same_jpg(listOfFileNames, first_posep)
                if not jpg:
                    logging.debug(f"We had a pose preset {first_posep} but didn't find the same jpg")
                else:
                    logging.debug(f"Found jpg {jpg[0].name}")
                    found = True
                    tags.add("Pose")
            if not found and cloth:
                first_cloth = list(cloth)[0]
                jpg = find_same_jpg(listOfFileNames, first_cloth)
                if not jpg:
                    logging.debug(f"We had a cloth {first_cloth} but didn't find the same jpg")
                else:
                    logging.debug(f"Found jpg {jpg[0].name}")
                    found = True
                    tags.add("Cloth")
            if not found and hair:
                first_hair = list(hair)[0]
                jpg = find_same_jpg(listOfFileNames, first_hair)
                if not jpg:
                    logging.debug(f"We had a hair {first_hair} but didn't find the same jpg")
                else:
                    logging.debug(f"Found jpg {jpg[0].name}")
                    found = True
                    tags.add("Hair")
            if not found and morph:
                first_morph = list(morph)[0]
                jpg = find_same_jpg(listOfFileNames, first_morph)
                if not jpg:
                    logging.debug(f"We had a morph {first_morph} but didn't find the same jpg")
                else:
                    logging.debug(f"Found jpg {jpg[0].name}")
                    found = True
                    tags.add("Morph")
            if not found and pose:
                first_pose = list(pose)[0]
                jpg = find_same_jpg(listOfFileNames, first_pose)
                if not jpg:
                    logging.debug(f"We had a pose {first_pose} but didn't find the same jpg")
                else:
                    logging.debug(f"Found jpg {jpg[0].name}")
                    found = True
                    tags.add("Pose")
            bfname = Path(fname).with_suffix('.jpg').name
            if found:
                logging.debug(f"We found jpg {jpg}")
                myvar.extract(jpg[0].name, outdir)
                set_tag(f"{Path(outdir,jpg[0].name)}", list(tags))
                logging.debug(f"Copying from {outdir}/{jpg[0].name} to {flatdirname}/{bfname}")
                shutil.copy(Path(outdir, jpg[0].name), Path(outdir, flatdirname, bfname))
            else:
                logging.debug("Didn't find a jpg")
                if save_scene:
                    tags.add("Scene")
                elif save_person or appear:
                    tags.add("Person")
                elif clothp:
                    tags.add("Cloth")
                elif hairp:
                    tags.add("Hair")
                elif morphp:
                    tags.add("Morph")
                elif posep:
                    tags.add("Pose")
                elif cloth:
                    tags.add("Cloth")
                elif hair:
                    tags.add("Hair")
                elif morph:
                    tags.add("Morph")
                elif pose:
                    tags.add("Pose")
                elif asset:
                    tags.add("Asset")
                elif script:
                    tags.add("Script")
                if not listOfJpg:
                    shutil.copy(ref_icon, Path(outdir, flatdirname, bfname))
                    set_tag(f"{Path(outdir, flatdirname, bfname)}", list(tags))
                else:
                    logging.debug(f"But we found these jpg:{listOfJpg}")
                    face_jpg = [ f for f in listOfJpg if "face" in f.lower() ]
                    if face_jpg:
                        jpg = face_jpg[0]
                    else:
                        jpg = listOfJpg[0]
                    myvar.extract(jpg, outdir)
                    set_tag(f"{Path(outdir,jpg)}", list(tags))
                    shutil.copy(Path(outdir,jpg), Path(outdir, flatdirname, bfname))

    except BadZipFile as e:
        logging.error(f"{fname} is not a correct zipfile ({e})")

def dep_fromvar(dir, var):
    try:
        var_file = vamdirs.find_var(dir, varname = var)
    except vamex.VarNotFound:
        # This happens if file names contain weird chars for windows
        # FIXME
#            Path(var).rename(Path(movepath, var_file.name))
        raise
    except vamex.VarNameNotCorrect:
        raise
    except Exception as e:
        logging.error("Uncaught exc %s"%e)
        raise

    try:
        meta = extract_meta_var(var_file)
    except vamex.VarMetaJson:
        raise

    if not( "dependencies" in meta and meta['dependencies']):
        return []

    return meta['dependencies']

def gen_meta(**kwargs):
    file_loader = FileSystemLoader('tpl')
    env = Environment(loader=file_loader)
    template = env.get_template('meta.json.j2')

    output = template.render(**kwargs)
    return output

def dep_fromscene(scene):

    def _decode_dict(a_dict):
        for id, ref in a_dict.items():  # pylint: disable=unused-variable
#            if id in ['id', 'uid', "url"]:
            if type(ref) == str:
                if ref.startswith("SELF:"):
                    deps['self'].append(ref)
                elif ":" in ref and not ref.startswith(':'):
                    name = ref.split(':')[0]
                    ndot = len(name.split('.'))
                    if ndot == 3:
                        deps['var'].append(ref)
                elif any(ref.endswith(s) for s in ['.vmi', ".vam", ".vap", ".json"]):
                    deps['embed'].append(ref)

    deps = { 'embed': [], 'var': [] , 'self': [] }
    with open(scene, "r") as fn:
        json.load(fn, object_hook=_decode_dict)
    return deps


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
                packageVersion = int(input("Give package version:"))
            except:
                print("Noo, I need an integer")
            else:
                break

    finalVar = f"{creatorName}.{packageName}.{packageVersion}"
    
    # Directory structure check
    for p in Path(input_dir).glob('**/*'):
        if p.is_dir():
            rp = Path(os.path.relpath(p, input_dir))
            if len(rp.parts)>1 and rp.parts[0] == "Saves" and rp.parts[1] != "scene":
                logging.error(f"Path {p} is not legal")
                ok = input("Abort? Hit simply Enter:")
                if not ok:
                    raise vamex.IllegalPath

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
            deps = dep_fromscene(scene)
            varnames = list(set([ v.split(':')[0] for v in deps['var'] ]))
            all_deps.extend(varnames)

    logging.info(f"Found deps:{all_deps}")
    # Filter stuffs
    # TODO

    logging.debug("Generating meta.json")
    _ = input(f"Last chance to copy/move files inside {Path(input_dir).resolve()}. Hit enter when ready to proceed:")
    meta_json = gen_meta(creatorName=creatorName, packageName=packageName, contents=contentsp, deps=all_deps)
    with open(f"{input_dir}/meta.json", "w") as meta_file: 
        meta_file.write(meta_json) 

    # We want files inside outdir
    logging.debug("Packing var file")
    with ZipFile(f'{finalVar}.var', 'w') as myzip:
        for file in Path(input_dir).glob('**/*'):
            myzip.write(filename = file, arcname = os.path.relpath(file, input_dir))

    # Remove tempdir and outdir
    if in_zipfile:
        shutil.rmtree(tempzipdir)



def get_type(infile):
    """
    From a file, detect resource type
    """
    infile = Path(infile)
    if infile.is_dir():
        return vamex.T_DIR
    suffix = infile.suffix
    if suffix == ".assetbundle" or suffix == ".scene":
        return vamex.T_ASSET
    if suffix == ".cs":
        return vamex.T_SCRIPT
    if suffix == ".json":
        with open(infile, "rt") as f:
            js = json.load(f)
            if "playerHeightAdjust" in js:
                return vamex.T_SCENE
            else:
                return vamex.T_POSE
    if suffix == ".vmi" or suffix == ".vmb":
        return vamex.T_MORPH
    if suffix == ".vam":
        with open(infile, "rt") as f:
            js = json.load(f)
            if js['itemType'] == "ClothingFemale":
                return vamex.T_CLOTH | vamex.T_FEMALE
            if js['itemType'] == "ClothingMale":
                return vamex.T_CLOTH | vamex.T_MALE
            if js['itemType'] == "HairFemale":
                return vamex.T_HAIR | vamex.T_FEMALE
            if js['itemType'] == "HairMale":
                return vamex.T_HAIR | vamex.T_MALE
    if suffix == ".vaj" or suffix == ".vab":
        return get_type(infile.with_suffix(".vam"))
    if suffix == ".vap":
        logging.warning("Didn't detect type of VAP")
        return vamex.T_VAP
    if suffix == ".jpg":
        logging.warning("Didn't detect type of JPG")
        return vamex.T_JPG
    
    return vamex.T_UNK

def get_reqfile(infile, mtype):
    infile=Path(infile)
    basedir=infile.parent
    req = set()
    req.add(infile)
    logging.debug(f"Search for associated files for {infile}")
    pic = list(Path(basedir).glob(f"**/{infile.with_suffix('.jpg').name}"))
    if pic and pic[0].is_file():
        req.add(pic[0])
    if mtype == vamex.T_ASSET or mtype == vamex.T_SCRIPT:
        pass
    elif mtype == vamex.T_SCENE or mtype == vamex.T_POSE:
        pass
    elif mtype & vamex.T_MORPH:
        vmi = list(Path(basedir).glob(f"**/{infile.with_suffix('.vmi').name}"))[0]
        vmb = list(Path(basedir).glob(f"**/{infile.with_suffix('.vmb').name}"))[0]
        if vmi.is_file() and vmb.is_file():
            req.add(vmi)
            req.add(vmb)
        else:
            logging.error(f"Missing files for {infile}")
            raise vamex.MissingFiles
    elif mtype & vamex.T_CLOTH or mtype & vamex.T_HAIR:
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
    elif mtype == vamex.T_JPG or mtype == vamex.T_VAP:
        pass
    else:
        logging.error(f"Can't detect required files for {infile} of type {mtype}")
        raise vamex.UnknownContent

    return list(req)

def prep_tree(file, dir, creator, do_move = False):

    # Get type
    mtype = get_type(file)
    logging.debug(f"Detected file {file} as type {mtype}")

    if mtype == vamex.T_DIR:
        # Copy subtree relative to a root (asked to user)
        parents = [ Path(file) ] 
        for p in Path(file).parents:
            parents.append(p)
        for i, p in enumerate(parents, start=1):
            tab='\t'
            print(f"{i}{tab}{p}")
        root = int(input("Select relative root dir:")) - 1
        reldir = parents[root]
        for f in Path(file).glob("**/*"):
            dir_in_target = Path(os.path.relpath(f, reldir)).parent
            dir_in_target_abs = Path(dir, dir_in_target)
            dir_in_target_abs.mkdir(parents=True, exist_ok=True)
            if do_move:
                shutil.move(f"{f}", f"{dir_in_target_abs}")
            else:
                shutil.copy(f, dir_in_target_abs)
        return

    # Require some files
    reqfiles = get_reqfile(file, mtype)
    nl = '\n'
    logging.debug(f"List of files:{nl}{nl.join(list(map(lambda x:x.as_posix(), reqfiles)))}")

    # Create dirstruct
    d = None
    if mtype == vamex.T_SCENE:
        d = Path(dir,"Saves", "scene")

    if mtype == vamex.T_ASSET:
        d = Path(dir,"Custom", "Assets", creator)

    if mtype & vamex.T_CLOTH:
        if mtype & vamex.T_FEMALE:
            gend = "Female"
        elif mtype & vamex.T_MALE:
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

    logging.debug(f"Puting file in {d.resolve()}")
    d.mkdir(parents=True, exist_ok=True)

    # Copy or Move files
    for f in reqfiles:
        if do_move:
            shutil.move(f"{f}", f"{d}")
        else:
            shutil.copy(f, d)
