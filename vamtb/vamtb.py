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

@cli.command('printdep')
@click.pass_context
def printdep(ctx):
    """Print dependencies of a var from reading meta. Recursive (will print deps of deps etc)"""
    vamdirs.recurse_dep(getdir(ctx), ctx.obj['file'], do_print = True)

@cli.command('printrealdep')
@click.pass_context
def printrealdep(ctx):
    """Print dependencies of a var from inspecting all json files. Not recursive"""
    try:
        deps = varfile.dep_fromvar(getdir(ctx), ctx.obj['file'])
    except vamex.VarNotFound:
        logging.error("Var not found!")
    else:
        for d in sorted(deps, key=str.casefold):
            print("%-60s : %s" % (d, ucol.greenf("Found") if vamdirs.exists_var(ctx.obj['dir'], d) else ucol.redf("Not found")))

@cli.command('checkdep')
@click.pass_context
def checkdep(ctx):
    """Check dependencies of a var"""
    vamdirs.recurse_dep(getdir(ctx), ctx.obj['file'], do_print = False)

@cli.command('dump')
@click.pass_context
def dumpvar(ctx):
    """Dump var meta.json"""
    pp = pprint.PrettyPrinter(indent=4)
    try:
        pp.pprint(varfile.extract_meta_var(vamdirs.find_var(getdir(ctx),ctx.obj['file'])))
    except vamex.VarNotFound as e:
        logging.error(f"Couldn't find var: {e}")
    except Exception as e:
        logging.error(f"Couldn't dump var: {e}")

@cli.command('noroot')
@click.pass_context
def noroot(ctx):
    """Remove root node stored in pose presets"""
    mdir = getdir(ctx)
    mfile = ctx.obj['file']
    var = vamdirs.find_var(mdir, mfile)
    logging.info(f"Removing root node from {var}")
    varfile.remroot(var)

@cli.command('sortvar')
@click.pass_context
def sort_vars(ctx):
    """Moves vars to subdirectory named by its creator"""
    mdir = getdir(ctx)
    logging.info("Sorting var in %s" % mdir)
    all_files = vamdirs.list_vars(mdir, pattern="*")
    vars_files = vamdirs.list_vars(mdir)
    mdir=Path(mdir)
    for var_file in vars_files:
        try:
            pass
            varfile.is_namecorrect(var_file)
        except vamex.VarNameNotCorrect:
            logging.error(f"File {var_file} has incorrect naming.")
            continue
        try:
            pass
            varfile.extract_meta_var(var_file)
        except vamex.VarMetaJson as e:
            logging.error(f"File {var_file} is corrupted [{e}].")
            continue
        except vamex.NoMetaJson as e:
            logging.error(f"File {var_file} doesn't have a meta.json file [{e}].")
            continue
        varfile.split_varname(var_file, dest_dir = mdir)
# FIXME too slow
#        jpg = varfile.find_same_jpg(all_files, var_file)
#        if jpg:
#            varfile.split_varname(jpg[0], dest_dir = mdir)

@cli.command('checkvars')
@click.pass_context
def check_vars(ctx):
    """Check all var files for consistency"""
    mdir=Path(getdir(ctx))
    logging.info("Checking dir %s for vars" % mdir)
    all_files = vamdirs.list_vars(mdir, pattern="*.var")
    logging.debug("Found %d files in %s" % (len(all_files), mdir))
    for file in all_files:
        try:
            varfile.is_namecorrect(file)
            dll = varfile.contains(file, ".dll")
            if dll:
                logging.warning(f"Var {file} contains dll files {','.join(dll)}")
        except vamex.VarNameNotCorrect:
            logging.error(f"Bad var {file}")

@cli.command('statsvar')
@click.pass_context
def stats_vars(ctx):
    """Get stats on all vars"""
    mdir=Path(getdir(ctx))
    logging.info("Checking stats for dir %s" % mdir)
    all_files = vamdirs.list_vars(mdir, pattern="*.var")
    creators_file = defaultdict(list)
    for file in all_files:
        creator, _ = file.name.split(".", 1)
        creators_file[creator].append(file.name)
    logging.debug("Found %d files in %s, %d creators" % (len(all_files), mdir, len(creators_file)))
    for k, v in reversed(sorted(creators_file.items(), key=lambda item: len(item[1]))):
        print("Creator %s has %d files" % (k, len(v)))

@cli.command('checkdeps')
@click.pass_context
def check_deps(ctx):
    """Check dependencies of all var files.
    When using -x, files considered bad due to Dep not found, Name not correct, meta JSON incorrect will be moved to 00Dep/.
    This directory can then be moved away from the directory.
    You can redo the same dependency check later by moving back the directory and correct vars will be moved out of the directory if they are now valid.
    """
    dir = getdir(ctx)
    move = ctx.obj['move']
    if move:
        movepath=Path(dir, "00Dep")
        Path(movepath).mkdir(parents=True, exist_ok=True)
    else:
        movepath=None
    logging.info(f'Checking deps for vars in {dir} with moving: {movepath is not None}')
    all_vars = vamdirs.list_vars(dir)
    missing = set()
    for var in sorted(all_vars):
        try:
            vamdirs.recurse_dep(dir, var.with_suffix('').name, do_print= False, strict=True)
        except vamex.VarNotFound as e:
            logging.error(ucol.redf(f'While handing var {var.name}, we got a {type(e).__name__} {e}'))
            missing.add(f"{e}")
            if movepath:
                Path(var).rename(Path(movepath, var.name))
        except (vamex.NoMetaJson, vamex.VarNameNotCorrect, vamex.VarMetaJson, vamex.VarExtNotCorrect, vamex.VarVersionNotCorrect) as e:
            logging.error(ucol.redf(f'While handing var {var.name}, we got {type(e).__name__} {e}'))
            if movepath:
                Path(var).rename(Path(movepath, var.name))
        except RecursionError:
            logging.error(ucol.redf(f"While handling var {var.name} we got a recursion error. This is pretty bad and the file should be removed."))
            exit(1)
        except Exception as e:
            logging.error(ucol.redf(f'While handing var {var.name}, caught exception {e}'))
            raise
    if missing:
        nl="\n"
        logging.error(ucol.redf(f'You have missing dependencies:{nl}{ nl.join( sorted(list(missing)) ) }'))
    else:
        logging.error(ucol.greenf("You have no missing dependency it seems. Yay!"))

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


@cli.command('dbs')
@click.pass_context
def dbs(ctx):
    """
    Scan vars and store props in db
    """
    mdir=Path(getdir(ctx))
    vars_files = sorted(vamdirs.list_vars(mdir))[0:]
    db.store_vars(vars_files)

@cli.command('dotty')
@click.pass_context
def dotty(ctx):
    """
    \b
    Gen dot graph of deps.
    If you only want to graph one var, use -f.
    """
    db.dotty(ctx.obj['file'])

@cli.command('dottys')
@click.pass_context
def dottys(ctx):
    """
    Gen dot graph of deps, one per var
    """
    mdir=Path(ctx.obj['dir'])
    vars_files = vamdirs.list_vars(mdir)
    for var_file in vars_files:
        var_file = Path(var_file).with_suffix('').name
        logging.info(f"Performing graph for {var_file}")
        db.dotty(var_file)


@cli.command('uiap')
@click.pass_context
def uiap(ctx):
    """Gen uia preset from var"""
    mdir=Path(getdir(ctx))
    mfile=ctx.obj['file']
    mvar, = vamdirs.list_vars(mdir, mfile)
    varfile.uiap(mvar)
