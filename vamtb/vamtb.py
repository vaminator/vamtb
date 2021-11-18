import logging
import locale
import os
import pprint
import sys
from collections import defaultdict
from pathlib import Path
import click
import shutil
from vamtb import vamdirs
from vamtb import varfile
from vamtb import vamex
from vamtb import db
from vamtb.utils import *

@click.group()
@click.option('dir', '-d', help='VAM directory (default cur dir).')
@click.option('custom', '-c', help='VAM custom directory.')
@click.option('file','-f', help='Var file.')
@click.option('-v', '--verbose', count=True, help="Verbose (twice for debug).")
@click.option('-x', '--move/--no-move', default=False, help="When checking dependencies move vars with missing dep in 00Dep. When repacking, move files rather than copying")
@click.pass_context
def cli(ctx, verbose, move, dir, custom, file):
    # pylint: disable=anomalous-backslash-in-string
    """ VAM Toolbox

    \b
    Dependency handling:
    vamtb -d d:\VAM -v checkdeps
    vamtb -d d:\VAM -vv -f sapuzex.Cooking_Lesson.1 checkdep
    vamtb -d d:\VAM -f ClubJulze.Bangkok.1 printdep
    vamtb -d d:\VAM -f ClubJulze.Bangkok.1 printrealdep
    \b
    Meta json handling:
    vamtb -d d:\VAM -f sapuzex.Cooking_Lesson.1 dump
    \b
    Thumb handling:
    vamtb -d d:\VAM thumb
    vamtb -d d:\VAM -f ClubJulze.Bangkok.1.var thumb
    \b
    Organizing:
    vamtb -d d:\VAM sortvar  Reorganize your var directories with <creator>/*
                If a file already exists in that directory, CRC is checked before overwritting.
    vamtb -d d:\VAM statsvar will dump some statistics    
    \b
    Building:
    vamtb -vvc d:\ToImport\SuperScene convert
    vamtb -x repack
    vamtb -d d:\VAM renamevar (caution this will rename vars based on meta.json creator and creation name)
    vamtb -d d:\VAM -f ClubJulze.Bangkok.1.var renamevar
    vamtb -d d:\VAM -f Community.PosePack.1 noroot  - Remove root node from poses (caution this will remove root node from pose, don't do this on scenes)
    vamtb -d d:\VAM -f Community.PosePack.1 uiap - Will generate uiap file containing pose presets, you then merge that to existing uiap 
    \b
    Database:
    vamtb -vvd d:\VAM dbs will scan your vars and create or if modification time is higher, update database 
    vamtb -vvd d:\VAM dotty will graph your collection
    vamtb -vvd d:\VAM -f sapuzex.Cooking_Lesson.1 dotty will graph this var
    vamtb -vvd d:\VAM dottys will graph each var seperately
    \b
    Character encoding on windows:
    On windows cmd will use cp1252 so you might get some errors displaying international characters.
    Start vamtb with python -X utf8 vamtb.py <rest of parameters>
    """
    logger = logging.getLogger()
    logging.basicConfig(level=("WARNING","INFO","DEBUG")[verbose], format='%(message)s')
    fh = logging.FileHandler('log-vamtb.txt', mode="w")
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    # fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    logging.info(ucol.greenf("Welcome to vamtb"))

    ctx.ensure_object(dict)
    ctx.obj['dir'] = dir
    ctx.obj['custom'] = custom
    ctx.obj['file'] = file
    ctx.obj['move'] = move
    sys.setrecursionlimit(100)  # Vars with a dependency depth of 100 are skipped

@cli.command('noroot')
@click.pass_context
def noroot(ctx):
    """Remove root node stored in pose presets"""
    mdir = getdir(ctx)
    mfile = ctx.obj['file']
    var = vamdirs.find_var(mdir, mfile)
    logging.info(f"Removing root node from {var}")
    varfile.remroot(var)

@cli.command('thumb')
@click.pass_context
def vars_thumb(ctx):
    """Gen thumbs from var file(s)"""
    basedir="thumb"
    mdir=Path(getdir(ctx))
    mfile=ctx.obj['file']
    if mfile:
        vars = vamdirs.list_vars(mdir, mfile)
    else:
        vars = vamdirs.list_vars(mdir)
    Path(basedir).mkdir(parents=True, exist_ok=True)
    logging.debug(f'Generating thumbs for vars')
    for var in vars:
        logging.debug(f"Extracting thumb from {var}")
        try:
            varfile.thumb_var( var, basedir)
        except vamex.VarNotFound as e:
            logging.error(f'Cannot find {var.name}')
        except Exception as e:
            logging.error(f'While handing var {var}, caught exception {e}')

@cli.command('convert')
@click.pass_context
def var_convert(ctx):
    """
    Convert tree to var.
    You can pass a file (considered a zipped var) with -f or a directory with -c.
    """
    # Used for excluding content already packaged and depending on it
    # dir=Path("%s/AddonPackages" % ctx.obj['dir'])
    file=ctx.obj['file']
    custom=ctx.obj['custom']
    logging.debug(f'Converting {custom} to var')

    try:
        varfile.make_var(custom, file, outdir="newvar")
    except Exception as e:
        logging.error(f'While handing var content, caught exception {e}')
        raise
    # We might want to move/archive the input_dir to avoid duplicates now
    # TODO

@cli.command('multiconvert')
@click.pass_context
def var_multiconvert(ctx):
    """
    Convert directory tree of directory trees to vars.
    Toplevel tree should be from the same creator with content in each subfolder.
    For each subfolder, a var with Creator.Content.1 will be created.
    """
    custom=ctx.obj['custom']
    logging.debug(f'Converting {custom} to var')

    creatorName = input("Give creator name:")
    for p in Path(custom).glob('*'):
        try:
            varfile.make_var(in_dir=p, in_zipfile=None, creatorName=creatorName, packageName=p.name, packageVersion=1, outdir="newvar")
        except Exception as e:
            logging.error(f'While handing directory {p}, caught exception {e}')
            raise

@cli.command('autoload')
@click.pass_context
def autoload(ctx):
    """Check vars having autoloading of morph
    """
    mdir=Path(getdir(ctx))
    vars_files = vamdirs.list_vars(mdir)
    for var_file in vars_files:
        try:
            json = varfile.extract_meta_var(var_file)
        except Exception as e:
            logging.error(f"Couldn't decode {var_file} [{e}]")
            continue
        if 'customOptions' in json and json['customOptions']['preloadMorphs'] != "false":
            vmi = varfile.pattern_var(var_file, r"\.vmi$")
            vmib = list(map(lambda x: x.split("/")[5], vmi))
            vmib = set(map(lambda x: x.split("/")[0], vmib))
            print(f"{var_file} has autoloading and contains morphs dirs: {vmib}")

@cli.command('repack')
@click.pass_context
def var_repack(ctx):
    """
    Convert single file to var.
    The creator name is asked and then you can drag and drop file names or directory names to the prompt.
    In case a directory is dragged and dropped you are prompted to give the root directory from which all files within this directory will be named in the meta.json file.
    Temporary content is tmp/. If you drag files, it is a good idea to begin with detectable types: scenes, person, .. as vamtby will create directory structure automatically.
    You can then drag and drop undetectable types (like jpg for textures) and vamtb will ask you where to place the files. Another method is to copy/move other content with explorer.
    Once you're ready, hit enter and the corresponding meta will be created.
    """
    custom = "tmp"
    move = ctx.obj['move']
    assert move, "Sorry but copy is broken on windows shit. Files/Dirs can only be moved from the source dir. Add -x"
    try:
        shutil.rmtree(custom)
    except:
        pass
    Path(custom).mkdir(parents=True, exist_ok=True)
    creatorName = input("Give creator name [Unknown]:")
    if not creatorName:
        creatorName = "Unknown"

    while "user didnt hit enter":
        file = input("Add file or directory (or hit enter to move to next step):")
        if file:
            if file.startswith('"') and file.endswith('"'):
                file=file[1:-1]
            logging.debug(f'Converting {file} to var')
            varfile.prep_tree(file, custom, creatorName, do_move=move)
        else:
            break

    logging.debug(f"Generating var from directory {custom}")

    try:
        varfile.make_var(custom, file, creatorName=creatorName, outdir="newvar")
    except Exception as e:
        logging.error(f'While handing directory {Path(custom).resolve()}, caught exception {e}')
        raise

@cli.command('renamevar')
@click.pass_context
def renamevar(ctx):
    """Rename var from meta.json"""
    mdir=Path(getdir(ctx))
    if ctx.obj['file']:
        mfile=ctx.obj['file']
        vars = vamdirs.list_vars(mdir, mfile)
    else:
        vars = vamdirs.list_vars(mdir)
    logging.debug(f'Renaming vars')
    for var in vars:
        logging.debug(f"Checking {var}")
        creator, asset, version, _ = var.name.split('.', 4)
        js = varfile.extract_meta_var(var)
        rcreator, rasset = js['creatorName'],js['packageName']
        if creator.replace(" ", "_") != rcreator.replace(" ", "_") or asset.replace(" ", "_") != rasset.replace(" ", "_"):
            rfile = Path(os.path.dirname(var), f"{rcreator}.{rasset}.{version}.var".replace(" ", "_"))
            logging.info(f"Renaming {var} to {rfile}")
            os.rename(var, rfile)

@cli.command('uiap')
@click.pass_context
def uiap(ctx):
    """Gen uia preset from var"""
    mdir=Path(getdir(ctx))
    print(mdir)
    mfile=ctx.obj['file']
    mvars = vamdirs.list_vars(fpath=mdir, pattern=mfile)
#    if len(mvars) == 1 and vars[0]:
#        var_path = mvars[0]
#    else:
#        logging.error("var not found")
#        exit(0)
    varfile.uiap(mvars[0])
