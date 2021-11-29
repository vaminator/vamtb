import os
import sys
import yaml
import zlib
import click
import shutil
from collections import defaultdict
from pathlib import Path
from tqdm import tqdm
from functools import wraps

from vamtb.graph import Graph
from vamtb.varfile import Var, VarFile
from vamtb.file import FileName
from vamtb import ref
from vamtb.vamex import *
from vamtb.log import *
from vamtb.utils import *

@click.group()
@click.option('file','-f', help='Var file to act on.')
@click.option('dir', '-d', help='Use a specific VAM directory.')
@click.option('-v', '--verbose', count=True, help="Verbose (twice for debug).")
@click.option('-x', '--move/--no-move', default=False, help="When checking dependencies move vars with missing dep in 00Dep.")
@click.pass_context
def cli(ctx, verbose, move, dir, file):
    # pylint: disable=anomalous-backslash-in-string
    """ VAM Toolbox

    \b
    Dependency handling (from disk)
    vamtb -d d:\VAM -v checkdeps
    vamtb -d d:\VAM -vv -f sapuzex.Cooking_Lesson.1 checkdep
    vamtb -d d:\VAM -f ClubJulze.Bangkok.1 printdep
    vamtb -d d:\VAM -f ClubJulze.Bangkok.1 printrealdep
    \b
    Meta json handling (from disk)
    vamtb -d d:\VAM -f sapuzex.Cooking_Lesson.1 dump
    \b
    Organizing (from disk)
    vamtb -d d:\VAM sortvar  Reorganize your var directories with <creator>/*
                If a file already exists in that directory, CRC is checked before overwritting.
    vamtb -d d:\VAM statsvar will dump some statistics    
    \b
    Database:
    vamtb -vvd d:\VAM dbs will scan your vars and create or if modification time is higher, update database 
    \b
    Dependency graph (uses database)
    vamtb -vvd d:\VAM dotty will graph your collection one graph per var
    vamtb -vvd d:\VAM -f sapuzex.Cooking_Lesson.1 dotty will graph this var
    vamtb -vvd d:\VAM -f sapuzex.* dotty will graph vars matching
    \b
    Character encoding on windows:
    On windows cmd will use cp1252 so you might get some errors displaying international characters.
    Start vamtb with python -X utf8 vamtb.py <rest of parameters>
    """

    log_setlevel(verbose)
    info("Welcome to vamtb")

    ctx.ensure_object(dict)
    ctx.obj['file']        = file
    ctx.obj['move']        = move
    ctx.obj['debug_level'] = verbose
    conf = {}
    
    try:
        with open(C_YAML, 'r') as stream:
            conf = yaml.load(stream, Loader=yaml.BaseLoader)
    except FileNotFoundError:
        conf['dir'] = input("Directory of Vam ?:")
        with open(C_YAML, 'w') as outfile:
            yaml.dump(conf, outfile, default_flow_style=False)
        info(f"Created {C_YAML}")
    except yaml.YAMLError as exc:
        error(f"YAML error in {C_YAML}: {exc}")

    dir = Path(conf['dir'])

    if dir.stem != "AddonPackages":
        dir = dir / "AddonPackages"

    if not ( dir.is_dir() and dir.exists() ):
        critical(f"AddonPackages '{dir}' is not existing directory", doexit=True)

    ctx.obj['dir'] = str(dir)

    sys.setrecursionlimit(100)  # Vars with a dependency depth of 100 are skipped

def catch_exception(func=None):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except VarNotFound as e:
            error(f"Var not found:{e}")
        except VarFileNameIncorrect as e:
            error(f"Var filename incorrect:{e}")
    return wrapper

@cli.command('printdep')
@catch_exception
@click.pass_context
def printdep(ctx):
    """Print dependencies of a var from reading meta. Recursive (will print deps of deps etc)"""
    file = ctx.obj['file']
    dir = ctx.obj['dir']
    file or critical("Need a file parameter", doexit=True)

    var = Var(file, dir)
    for depvar in sorted(var.dep_frommeta(), key=str.casefold):
        try:
            var = Var(depvar, dir)
        except VarNotFound:
            mess = red("Not found")
        else:
            mess = green("Found")
        print(f"{depvar:<60}: {mess}")

@cli.command('printrealdep')
@click.pass_context
@catch_exception
def printrealdep(ctx):
    """Print dependencies of a var from inspecting all json files. Not recursive"""
    file = ctx.obj['file']
    dir = ctx.obj['dir']
    file or critical("Need a file parameter", doexit=True)

    var = Var(file, dir)
    deps = var.dep_fromfiles()
    for depvar in sorted(deps, key=str.casefold):
        mess = green("Found")
        try:
            var = Var(depvar, dir)
        except VarNotFound:
            mess = red("Not found")
        else:
            mess = green("Found")
        print(f"{depvar:<60}: {mess}")

@cli.command('dump')
@click.pass_context
@catch_exception
def dumpvar(ctx):
    """Dump var meta.json"""
    file = ctx.obj['file']
    dir = ctx.obj['dir']
    file or critical("Need a file parameter", doexit=True)
    with Var(file, dir) as var:
        print(prettyjson( var.load_json_file("meta.json") ))

@cli.command('noroot')
@click.pass_context
@catch_exception
def noroot(ctx):
    """Remove root node stored in pose presets"""
    file = ctx.obj['file']
    dir = ctx.obj['dir']
    file or critical("Need a file parameter", doexit=True)
    with Var(file, dir) as var:
        var.remroot()

@cli.command('sortvar')
@click.pass_context
@catch_exception
def sort_vars(ctx):
    """Moves vars to subdirectory named by its creator"""
    dir = ctx.obj['dir']
    info(f"Sorting var in {dir}")
    for file in search_files_indir(dir, "*.var"):
        try:
            with Var(file, dir) as var:
                var.move_creator()
        except zlib.error:
            error(f"Zip error on var {file}")

@cli.command('checkvars')
@click.pass_context
@catch_exception
def check_vars(ctx):
    """Check all var files for consistency"""
    dir = ctx.obj['dir']
    file = ctx.obj['file']
    info(f"Checking vars in {dir}")
    if file:
        pattern = VarFile(file).file
    else:
        pattern = "*.var"
    for file in search_files_indir(dir, pattern):
        try:
            with Var(file, dir, zipcheck=True) as var:
                info(f"{var} is OK")
        except KeyboardInterrupt:
            return
        except Exception as e:
            error(f"{file} is not OK [{e}]")

@cli.command('statsvar')
@click.pass_context
@catch_exception
def stats_vars(ctx):
    """Get stats on all vars"""
    dir = ctx.obj['dir']
    info(f"Checking vars in {dir}")
    creators_file = defaultdict(list)
    for file in search_files_indir(dir, "*.var"):
        try:
            with Var(file, dir) as var:
                creators_file[var.creator].append(var.var)
        except KeyboardInterrupt:
            return
        except Exception as e:
            error(f"{file} is not OK [{e}]")
    for k, v in reversed(sorted(creators_file.items(), key=lambda item: len(item[1]))):
        print("Creator %s has %d files" % (k, len(v)))

@cli.command('checkdeps')
@click.pass_context
@catch_exception
def checkdeps(ctx):
    """Check dependencies of all var files.
    When using -x, files considered bad will be moved to directory "00Dep".
    This directory can then be moved away from the directory.
    You can redo the same dependency check later by moving back the directory and correct vars will be moved out of this directory if they are now valid.
    """
    move = ctx.obj['move']
    dir = ctx.obj['dir']
    file = ctx.obj['file']

    full_bad_dir = Path(dir) / C_BAD_DIR

    if move:
        list_move = []
        movepath = Path(dir, C_BAD_DIR)
        Path(movepath).mkdir(parents=True, exist_ok=True)
    if file:
        pattern = VarFile(file).file
    else:
        pattern = "*.var"
    for file in search_files_indir(dir, pattern):
        try:
            with Var(file, dir) as var:
                try:
                    _ = var.depend(recurse=True)
                except (VarNotFound, zlib.error) as e:
                    error(f'Missing or wrong dependency for {var} [{e}]')
                    if move:
                        try:
                            shutil.copy(var.path, str(full_bad_dir))
                        except shutil.SameFileError:
                            dvar = Path(full_bad_dir) / var.file
                            scrc = var.crc
                            dcrc = FileName(dvar).crc
                            if scrc == dcrc:
                                os.remove(var.path)
                            else:
                                error(f"Can't move {var} (crc {scrc}) as {dvar} exists with diferent crc ({dcrc})")

                        except shutil.Error:
                            # File is already there
                            pass
                            raise
                        else:
                            print(f"Moved {var} to {full_bad_dir}")
        except (VarExtNotCorrect, VarMetaJson, VarNameNotCorrect, VarVersionNotCorrect):
            pass


@cli.command('dbs')
@click.pass_context
@catch_exception
def dbs(ctx):
    """
    Scan vars and store props in db
    """
    stored = 0
    dir = ctx.obj['dir']
    file = ctx.obj['file']
    if file:
        pattern = VarFile(file).file
    else:
        pattern = "*.var"

    vars_list = search_files_indir(dir, pattern)
    if ctx.obj['debug_level']:
        iterator = vars_list
    else:
        iterator = tqdm(vars_list, desc="Writing database…", ascii=True, maxinterval=5, ncols=75, unit='var')
    for varfile in iterator:
        with Var(varfile, dir, use_db=True) as var:
            if var.store_var():
                stored += 1
    info(f"{stored} var files stored")

@cli.command('dotty')
@click.pass_context
@catch_exception
def dotty(ctx):
    """
    Gen dot graph of deps, one per var
    """
    if shutil.which(C_DOT) is None:
        critical(f"Make sure you have graphviz installed in {C_DOT}.", doexit=True)

    dir =Path(ctx.obj['dir'])
    file = ctx.obj['file']
    if file:
        pattern = f"*{file}*"
    else:
        pattern = "*.var"
    for varfile in search_files_indir(dir, pattern):
        info(f"Calculating dependency graph of {VarFile(varfile).var}")
        with Var(varfile, dir, use_db=True) as var:
            Graph.dotty(var)

@cli.command('reref')
@click.pass_context
@catch_exception
def reref(ctx):
    """
    Reref var: embedded content is removed, its reference is converted to real reference and dependency on the reference is added.
    """
    dir =Path(ctx.obj['dir'])
    file = ctx.obj['file']
    if file:
        pattern = f"*{file}*"
    else:
        pattern = "*.var"
    for varfile in search_files_indir(dir, pattern):
        with Var(varfile, dir, zipcheck=True) as var:
            ref.reref_var(var)

@cli.command('dupinfo')
@click.pass_context
@catch_exception
def dupinfo(ctx):
    """
    Return duplication information for file(s)
    """
    dir =Path(ctx.obj['dir'])
    file = ctx.obj['file']
    if file:
        pattern = f"*{file}*"
    else:
        pattern = "*.var"
    for varfile in search_files_indir(dir, pattern):
        with Var(varfile, dir, use_db=True) as var:
            dups = var.dupinfo()
            ndup, sdup = dups['numdupfiles'], dups['dupsize']
            ntot = var.get_numfiles()
            msg= f"{var.var:<64} : Dups:{ndup:<5}/{ntot:<5} Dup Size:{toh(sdup):<10} (ref:{var.get_ref})"
            if not ndup:
                msg = green(msg)
            elif ndup < C_MAX_FILES and sdup < C_MAX_SIZE:
                msg = blue(msg)
            else:
                msg = red(msg)
            print(msg)
