import logging
import os
import sys
from vamtb.file import FileName
import yaml
from collections import defaultdict
from pathlib import Path

from vamtb.graph import Graph
import click
import shutil
from vamtb.varfile import Var, VarFile
from vamtb.vamex import *
from vamtb import db
from vamtb.log import *
from vamtb.utils import *
import zlib

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
    ctx.obj['file']     = file
    ctx.obj['move']     = move
    conf = {}
    try:
        with open(C_YAML, 'r') as stream:
            conf = yaml.load(stream, Loader=yaml.BaseLoader)
    except FileNotFoundError:
        pass
    except yaml.YAMLError as exc:
        error("YAML error %s", exc)

    if not conf:
        conf['dir'] = input("Directory of Vam ?:")
        with open(C_YAML, 'w') as outfile:
            yaml.dump(conf, outfile, default_flow_style=False)
        info(f"Created {C_YAML}")

    dir = conf['dir']
    if not str(Path(dir)).endswith("AddonPackages"):
        dir = str(Path(dir, "AddonPackages"))

    ctx.obj['dir'] = dir

    sys.setrecursionlimit(100)  # Vars with a dependency depth of 100 are skipped

""" def catch_exception(func=None, *, handle):
    if not func:
        return partial(catch_exception, handle=handle)

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except handle as e:
            raise click.ClickException(e)

    return wrapper
 """
def catch_exception(func=None):
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

    var = Var(multiFileName=file, dir= dir)
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

#@cli.command('checkdep')
#@click.pass_context
#def checkdep(ctx):
#    """Check dependencies of a var"""
#    file = ctx.obj['file']
#    dir = ctx.obj['dir']
#    move = ctx.ob
#    with Var(file, dir) as var:
#        var.depend(recurse = True)

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
    dir = ctx.obj['dir']
    file = ctx.obj['file']
    if file:
        pattern = VarFile(file).file
    else:
        pattern = "*.var"
    db.store_vars(search_files_indir(dir, pattern))

@cli.command('dotty')
@click.pass_context
@catch_exception
def dotty(ctx):
    """
    Gen dot graph of deps, one per var
    """
    mdir=Path(ctx.obj['dir'])
    file = ctx.obj['file']
    if file:
        pattern = f"*{file}*"
    else:
        pattern = "*.var"
    graph = Graph()
    for var_file in search_files_indir(mdir, pattern):
        info(f"Calculating dependency graph of {VarFile(var_file).var}")
        graph.dotty(var_file)
