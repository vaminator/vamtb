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
from PIL import Image

def split_varname(fname, dest_dir):
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
    fname = Path(name).with_suffix('').name
    candidates = [ f for f in listFiles if f.lower().endswith(f"{fname.lower()}.jpg") ]
    return candidates

def thumb_var2(fname, outdir):
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
                        exit(1)
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
                    logging.debug(f"Found jpg {jpg[0]}")
                    found = True
                    tags.add("Scene")
            if not found and save_person:
                first_person = list(save_person)[0]
                jpg = find_same_jpg(listOfFileNames, first_person)
                if not jpg:
                    logging.debug(f"We had a person {first_person} but didn't find the same jpg")
                else:
                    logging.debug(f"Found jpg {jpg[0]}")
                    found = True
                    tags.add("Person")
            if not found and appear:
                first_person = list(appear)[0]
                jpg = find_same_jpg(listOfFileNames, first_person)
                if not jpg:
                    logging.debug(f"We had a person appearance {first_person} but didn't find the same jpg")
                else:
                    logging.debug(f"Found jpg {jpg[0]}")
                    found = True
                    tags.add("Person")
            if not found and clothp:
                first_clothp = list(clothp)[0]
                jpg = find_same_jpg(listOfFileNames, first_clothp)
                if not jpg:
                    logging.debug(f"We had a cloth preset {first_clothp} but didn't find the same jpg")
                else:
                    logging.debug(f"Found jpg {jpg[0]}")
                    found = True
                    tags.add("Cloth")
            if not found and hairp:
                first_hairp = list(hairp)[0]
                jpg = find_same_jpg(listOfFileNames, first_hairp)
                if not jpg:
                    logging.debug(f"We had a hair preset {first_hairp} but didn't find the same jpg")
                else:
                    logging.debug(f"Found jpg {jpg[0]}")
                    found = True
                    tags.add("Hair")
            if not found and morphp:
                first_morphp = list(morphp)[0]
                jpg = find_same_jpg(listOfFileNames, first_morphp)
                if not jpg:
                    logging.debug(f"We had a morph preset {first_morphp} but didn't find the same jpg")
                else:
                    logging.debug(f"Found jpg {jpg[0]}")
                    found = True
                    tags.add("Morph")
            if not found and posep:
                first_posep = list(posep)[0]
                jpg = find_same_jpg(listOfFileNames, first_posep)
                if not jpg:
                    logging.debug(f"We had a pose preset {first_posep} but didn't find the same jpg")
                else:
                    logging.debug(f"Found jpg {jpg[0]}")
                    found = True
                    tags.add("Pose")
            if not found and cloth:
                first_cloth = list(cloth)[0]
                jpg = find_same_jpg(listOfFileNames, first_cloth)
                if not jpg:
                    logging.debug(f"We had a cloth {first_cloth} but didn't find the same jpg")
                else:
                    logging.debug(f"Found jpg {jpg[0]}")
                    found = True
                    tags.add("Cloth")
            if not found and hair:
                first_hair = list(hair)[0]
                jpg = find_same_jpg(listOfFileNames, first_hair)
                if not jpg:
                    logging.debug(f"We had a hair {first_hair} but didn't find the same jpg")
                else:
                    logging.debug(f"Found jpg {jpg[0]}")
                    found = True
                    tags.add("Hair")
            if not found and morph:
                first_morph = list(morph)[0]
                jpg = find_same_jpg(listOfFileNames, first_morph)
                if not jpg:
                    logging.debug(f"We had a morph {first_morph} but didn't find the same jpg")
                else:
                    logging.debug(f"Found jpg {jpg[0]}")
                    found = True
                    tags.add("Morph")
            if not found and pose:
                first_pose = list(pose)[0]
                jpg = find_same_jpg(listOfFileNames, first_pose)
                if not jpg:
                    logging.debug(f"We had a pose {first_pose} but didn't find the same jpg")
                else:
                    logging.debug(f"Found jpg {jpg[0]}")
                    found = True
                    tags.add("Pose")
            bfname = Path(fname).with_suffix('.jpg').name
            if found:
                logging.debug(f"We found jpg {jpg}")
                myvar.extract(jpg[0], outdir)
                set_tag(f"{Path(outdir,jpg[0])}", list(tags))
                logging.debug(f"Copying from {outdir}/{jpg[0]} to {flatdirname}/{bfname}")
                shutil.copy(Path(outdir, jpg[0]), Path(outdir, flatdirname, bfname))
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
                    tags.add("Morph")
                elif cloth:
                    tags.add("Cloth")
                elif hair:
                    tags.add("Hair")
                elif morph:
                    tags.add("Morph")
                elif pose:
                    tags.add("Morph")
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
        logging.error(f"{fname} is not a correct zipfile")
    except Exception as e:
        logging.error(f"Got exception {e} Trace {traceback.format_exc()}")
        exit(0)

def gen_meta(**kwargs):
    file_loader = FileSystemLoader('tpl')
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

    logging.debug(f"Input is {input_dir}")

    # Detect properties (from vmi, from TODO?? )
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
    
    # List files relative to basedir
    contents = list( Path(os.path.relpath(x, input_dir)) for x in Path(input_dir).glob('**/*') if x.is_file() and x.name!="meta.json" )
    logging.debug(f"Found {len(contents)} elements in {input_dir}")    
    # Solve dependencies stuffs
    # TODO

    # Filter stuffs
    # TODO

    logging.debug("Generating meta.json")
    meta_json = gen_meta(creatorName=creatorName, packageName=packageName, contents=contents)
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
    