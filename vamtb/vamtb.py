import os
import sys
import yaml
import zlib
import click
import shutil
from collections import defaultdict
from pathlib import Path
from tqdm import tqdm

from vamtb.graph import Graph
from vamtb.var import Var
from vamtb.file import FileName
from vamtb.vamex import *
from vamtb.log import *
from vamtb.utils import *
from vamtb.varfile import VarFile
from vamtb.db import Dbs

@click.group()
@click.option('-a', '--force/--no-force', default=False,        help="Do not ask for confirmation.")
@click.option('-b', '--usedb/--no-usedb', default=False,        help="Use DB.")
@click.option('dir', '-d',                                      help='Use a specific VAM directory.')
@click.option('-c', '--cc/--no-cc', default=False,              help="Only upload CC license content")
@click.option('-e', '--meta/--no-meta', default=False,          help="Only reset subject metadata.")
@click.option('file','-f',                                      help='Var file to act on.')
@click.option('iaprefix','-i',                                  help=f'Internet Archive identifier prefix (defaults to {IA_IDENTIFIER_PREFIX}).')
@click.option('-m', '--move/--no-move', default=False,          help="When checking dependencies move vars with missing dep in 00Dep.")
@click.option('-n', '--dryrun/--no-dryrun', default=False,      help="Dry run on what would be uploaded.")
@click.option('-p', '--progress/--no-progress', default=False,  help="Add progress bar.")
@click.option('-q', '--remove/--no-remove', default=False,      help="Remove var from DB.")
@click.option('-r', '--ref/--no-ref', default=False,            help="Only select non reference vars for dupinfo.")
@click.option('-s', '--full/--no-full', default=False,          help="For scenes, upload not only scene jpg but all jpg to IA.")
@click.option('-v', '--verbose', count=True,                    help="Verbose (twice for debug).")
@click.option('dup', '-x',                                      help='Only dedup this file.')
@click.option('-z', '--setref/--no-setref', default=False,      help="Set var as reference.")
@click.pass_context
def cli(ctx, verbose, move, ref, usedb, dir, file, dup, remove, setref, force, meta, progress, dryrun, full, cc, iaprefix):
    # pylint: disable=anomalous-backslash-in-string
    """ VAM Toolbox

    \b
    Dependency handling (from disk or database):
    vamtb checkdeps
    vamtb -f sapuzex.Cooking_Lesson.1 checkdeps
    vamtb -f -b sapuzex.Cooking_Lesson.1 checkdep
    vamtb -f ClubJulze.Bangkok.1 printdep
    vamtb -f ClubJulze.Bangkok.1 printrealdep
    \b
    Meta json handling (from disk):
    vamtb -f sapuzex.Cooking_Lesson.1 dump
    \b
    Organizing (from disk):
    vamtb sortvar  Reorganize your var directories with <creator>/*
                If a file already exists in that directory, CRC is checked before overwritting.
    vamtb statsvar will dump some statistics    
    \b
    Database:
    vamtb dbsscan will scan your vars and create or if modification time is higher, update database 
    vamtb -f sapuzex.Cooking_Lesson.1 dbdel will remove any reference to var and files in the DB
    \b
    Dependency graph (uses database):
    vamtb graph will graph your collection one graph per var
    vamtb -f sapuzex.Cooking_Lesson.1 graph will graph this var
    vamtb -f sapuzex.* graph will graph vars matching
    \b
    Deduplication (uses database):
    vamtb -f sapuzex.Cooking_Lesson.1 dupinfo will print duplication info
    vamtb -f Wolverine333.% reref will dedup files from creator
    vamtb -x colorcorrect.assetbundle reref will remove all embedded colorcorrect.assetbundle from every var BUT the reference var
    \b
    Upload (uses database):
    vamtb -f sapuzex.Cooking_Lesson.1 ia will upload each var to an Internet Archive item
    vamtb -f sapuzex.Cooking_Lesson.1 anon will upload each var to anonfiles (need an account for the API key)

    \b
    File filters:
    You can use wildcards with % caracter: vamtb -f Community.% dupinfo
    \b
    You can get help for a command with
    vamtb <command> --help

    """

    log_setlevel(verbose)
    info("Welcome to vamtb")

    ctx.ensure_object(dict)
    ctx.obj['file']        = file
    ctx.obj['move']        = move
    ctx.obj['ref']         = ref
    ctx.obj['usedb']       = usedb
    ctx.obj['debug_level'] = verbose
    ctx.obj['progress']    = progress
    ctx.obj['dup']         = dup
    ctx.obj['remove']      = remove
    ctx.obj['setref']      = setref
    ctx.obj['force']       = force
    ctx.obj['meta']        = meta
    ctx.obj['dryrun']      = dryrun
    ctx.obj['full']        = full
    ctx.obj['cc']          = cc
    ctx.obj['iaprefix']    = iaprefix
    conf = {}
    try:
        with open(C_YAML, 'r') as stream:
            conf = yaml.load(stream, Loader=yaml.BaseLoader)
    except FileNotFoundError:
        conf['dir'] = input(blue("Directory of Vam ?:"))
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

@cli.command('printdep')
@catch_exception
@click.pass_context
def printdep(ctx):
    """Print dependencies of a var from reading meta. 


    vamtb [-vv] [-f <file pattern> ] printdep

    Recursive (will print deps of deps etc)"""

    file, dir, pattern = get_filepattern(ctx)
    for varfile in search_files_indir(dir, pattern):
        with Var(file, dir) as var:
            depvarfiles = sorted(var.dep_frommeta(), key=str.casefold)
            print(f"Printing dependencies for {green(var.var):<50} : {len(depvarfiles) if len(depvarfiles) else 'No'} dependencies")
            for depvarfile in sorted(var.dep_frommeta(), key=str.casefold):
                try:
                    _ = Var(depvarfile, dir)
                except VarNotFound:
                    mess = red("Not found")
                else:
                    mess = green("Found")
                print(f"{depvarfile:<68}: {mess}")

@cli.command('printrealdep')
@click.pass_context
@catch_exception
def printrealdep(ctx):
    """Print dependencies of a var from inspecting all json files. 


    vamtb [-vv] [-f <file pattern> ] printrealdep

    Not recursive"""
    file, dir, pattern = get_filepattern(ctx)
    for varfile in search_files_indir(dir, pattern):
        with Var(varfile, dir) as var:
            deps = list(set(var.dep_fromfiles()))
            depvarfiles = sorted(deps, key=str.casefold)
            print(f"Printing dependencies for {green(var.var):<50} : {len(depvarfiles) if len(depvarfiles) else 'No'} dependencies")
            for depvarfile in depvarfiles:
                #var.license
                xvar = VarFile(depvarfile).var_nov
                with Var(depvarfile, dir, use_db=True) as dvar:
                    xlicense = Var(dvar.latest(), dir, use_db=True).license
                s=( f'"{xvar}.latest":{{\n'
                    f'    "licenseType" : "{xlicense}",\n'
                     '    "dependencies" : {}\n'
                     '},'
                )
                print(s)
                continue
                mess = green("Found")
                try:
                    _ = Var(depvarfile, dir)
                except VarNotFound:
                    mess = red("Not found")
                else:
                    mess = green("Found")
                print(f"{depvarfile:<68}: {mess}")

@cli.command('dump')
@click.pass_context
@catch_exception
def dumpvar(ctx):
    """Dump meta.json from var.


    vamtb [-vv] -f <file pattern> dumpvar
    
    """
    file, dir, pattern = get_filepattern(ctx)
    file or critical("Need a file parameter", doexit=True)
    with Var(file, dir) as var:
        print(prettyjson( var.load_json_file("meta.json") ))

@cli.command('noroot')
@click.pass_context
@catch_exception
def noroot(ctx):
    """Remove root node stored in pose presets.


    vamtb [-vv] -f <file pattern> noroot

    """
    file, dir, pattern = get_filepattern(ctx)
    file or critical("Need a file parameter", doexit=True)
    with Var(file, dir) as var:
        var.remroot()

@cli.command('sortvar')
@click.pass_context
@catch_exception
def sort_vars(ctx):
    """Moves vars to subdirectory named by its creator.


    vamtb [-vv] [-f <file pattern> ] sortvar
    
    Crc is checked before erasing duplicates"""

    file, dir, pattern = get_filepattern(ctx)
    info(f"Sorting var in {dir}")
    for file in search_files_indir(dir, pattern):
        try:
            with Var(file, dir) as var:
                var.move_creator()
        except zlib.error:
            error(f"Zip error on var {file}")

@cli.command('checkvar')
@click.pass_context
@catch_exception
def check_vars(ctx):
    """Check all var files for consistency. All vars content found on disk are extracted for verification.


    vamtb [-vv] [-p] [-f <file pattern> ] checkvar

    -p: progress bar
    """

    file, dir, pattern = get_filepattern(ctx)
    vars_list = search_files_indir(dir, pattern)
    if ctx.obj['progress'] == False or ctx.obj['debug_level']:
        iterator = vars_list
    else:
        iterator = tqdm(vars_list, desc="Checking vars…", ascii=True, maxinterval=3, ncols=75, unit='var')
    for file in iterator:
        try:
            with Var(file, dir, checkVar=True) as var:
                try:
                    _ = var.meta()
                except FileNotFoundError:
                    error(f"Var {var.var} does not contain a correct meta json file")
                else:
                    info(f"{var} is OK")
        except KeyboardInterrupt:
            return
        except Exception as e:
            error(f"{file} is not OK [{e}]")

@cli.command('statsvar')
@click.pass_context
@catch_exception
def stats_vars(ctx):
    """Get stats on all vars.


    vamtb [-vv] [-f <file pattern> ] statsvar

    """

    file, dir, pattern = get_filepattern(ctx)
    info(f"Checking vars in {dir}")
    creators_file = defaultdict(list)
    for mfile in search_files_indir(dir, pattern):
        try:
            with Var(mfile, dir) as var:
                creators_file[var.creator].append(var.var)
        except KeyboardInterrupt:
            return
        except Exception as e:
            error(f"{mfile} is not OK [{e}]")
    for k, v in reversed(sorted(creators_file.items(), key=lambda item: len(item[1]))):
        print("Creator %s has %d files" % (k, len(v)))

@cli.command('checkdep')
@click.pass_context
@catch_exception
def checkdep(ctx):
    """Check dependencies of var recursively.


    vamtb [-vv] [-m] [-b] [-f <file pattern> ] checkdep

    When using -m, files considered bad will be moved to directory "00Dep". This directory can then be moved away from the directory.

    When using -b, use database rather than file system.

    You can redo the same dependency check later by moving back the directory and correct vars will be moved out of this directory if they are now valid.
    """
    move = ctx.obj['move']
    usedb = ctx.obj['usedb']

    file, dir, pattern = get_filepattern(ctx)
    if move:
        full_bad_dir = Path(dir) / C_BAD_DIR
        full_bad_dir.mkdir(parents=True, exist_ok=True)
    stop = True if move else False

    for mfile in sorted(search_files_indir(dir, pattern)):
        try:
            with Var(mfile, dir, use_db=usedb) as var:
                try:
                    if usedb:
                        _ = var.rec_dep(stop=stop)
                    else:
                        _ = var.depend(recurse=True, stop=stop)
                except (VarNotFound, zlib.error) as e:
                    error(f'Missing or wrong dependency for {var} [{e}]')
                    if move:
                        try:
                            shutil.copy(var.path, str(full_bad_dir))
                            os.remove(var.path)
                        except shutil.SameFileError:
                            dvar = full_bad_dir / var.file
                            scrc = var.crc
                            dcrc = FileName(dvar).crc
                            if scrc == dcrc:
                                os.remove(var.path)
                            else:
                                error(f"Can't move {var} (crc {scrc}) as {dvar} exists with diferent crc ({dcrc})")

                        except shutil.Error:
                            # Old code for older python
                            assert(False)
                        else:
                            print(f"Moved {var} to {full_bad_dir}")
        except (VarExtNotCorrect, VarMetaJson, VarNameNotCorrect, VarVersionNotCorrect):
            # info(f"Wrong file {mfile}")
            pass


@cli.command('dbscan')
@click.pass_context
@catch_exception
def dbscan(ctx):
    """
    Scan vars and store props in db.


    vamtb [-vv] [-a] [-p] [-f <file pattern> ] dbscan

    -p: Display progress bar (only when not using -v)                                  
    -a: Do not confirm, always answer yes (will overwrite DB with new content)
    """

    stored = 0
    quiet = False if ctx.obj['debug_level'] else True
    file, dir, pattern = get_filepattern(ctx)
    vars_list = search_files_indir(dir, pattern)
    if not quiet or ctx.obj['progress'] == False:
        iterator = vars_list
    else:
        iterator = tqdm(vars_list, desc="Writing database…", ascii=True, maxinterval=3, ncols=75, unit='var')
    for varfile in iterator:
        with Var(varfile, dir, use_db=True, check_exists=False) as var:
            try:
                if var.store_update(confirm=False if ctx.obj['force'] else True):
                    stored += 1
            except VarMalformed as e:
                error(f"Var {var.var} malformed [{e}].")
    info(f"{stored} var files stored")


@cli.command('dbclean')
@click.pass_context
def dbclean(ctx):
    """
    Remove vars from DB which are not found on disk.

    vamtb [-vv] [-a] dbscan

    -a: Always delete without prompting
    """

    files = search_files_indir(ctx.obj['dir'], f"*.var", ign=True)
    varnames = set([ e.with_suffix("").name for e in files ])
    dbvars = set(Dbs.get_vars())
    diff = sorted(list(varnames - dbvars) + list(dbvars - varnames))
    for var in diff:
        print(f"Var {red(var)} is in DB but not on disk  ")
        if ctx.obj['force'] or input("Delete from DB: Y [N] ?").upper() == "Y":
            varfile = VarFile(var, use_db=True)
            print(f"Deleting {varfile.file}")
            varfile.db_delete()
            varfile.db_commit()
            info(f"Removed {var} from DB")


@cli.command('graph')
@click.pass_context
@catch_exception
def dotty(ctx):
    """
    Generate graph of deps, one per var.


    vamtb [-vv] [-f <file pattern> ] graph

    """
    if shutil.which(C_DOT) is None:
        critical(f"Make sure you have graphviz installed in {C_DOT}.", doexit=True)

    file, dir, pattern = get_filepattern(ctx)
    for varfile in search_files_indir(dir, pattern):
        with Var(varfile, dir, use_db=True) as var:
            info(f"Calculating dependency graph for {var.var}")
            Graph.dotty(var)

@cli.command('reref')
@click.pass_context
@catch_exception
def reref(ctx):
    """
    Remove embedded content and point to reference var.


    vamtb [-vv] [-f <file pattern> ] [-x reference_to_remove.xxx] reref

    -a: Do not confirm, always answer yes (there will still be a prompt if there's two reference)
    -f: will operate only on this var                                          
    -x: will remove only this embedded content
    """
    dup = ctx.obj['dup']
    file, dir, pattern = get_filepattern(ctx)
    creator = ""
    critical("Be cautious with what you accept (Y). If some bundled content was modified, you might get some split content.")
    critical("Also vars referencing this content will have broken dependencies. Check that manually for now.")
    for varfile in search_files_indir(dir, pattern):
        with Var(varfile, dir, use_db=True) as var:
            msg = f"Reref on {varfile.name:<100} size:"
            if not var.exists():
                print(red(f"{msg} UNKNOWN"))
                continue
            print(green(f"{msg} {toh(var.size)}"))
            if var.creator == creator:
                debug("Skipping creator..")
                continue
            if var.exists():
                res = var.reref(dryrun=False, dup=dup, confirm=not ctx.obj['force'])
                if res and res == C_NEXT_CREATOR:
                    creator = var.creator
                else:
                    creator = ""
            else:
                warn(f"{var.var} exists as {var.path} but is not in the DB, skipping..")

@cli.command('dupinfo')
@click.pass_context
@catch_exception
def dupinfo(ctx):
    """
    Return duplication information.


    Will print in red vars which have either 50 dup files or +20MB dup content

    vamtb [-vv] [-r] [-f <file pattern> ] dupinfo

    -r : only scan vars from creators not part of "references"
    """
    onlyref = ctx.obj['ref']
    file, dir, pattern = get_filepattern(ctx)
    for varfile in search_files_indir(dir, pattern):
        with Var(varfile, dir, use_db=True) as var:
            if not file and onlyref:
                if var.get_ref == "YES":
                    continue
            dups = var.dupinfo()
            ndup, sdup = dups['numdupfiles'], dups['dupsize']
            if not file and not ndup:
                continue 
            ntot = var.get_numfiles()
            msg= f"{var.var:<64} : Dups:{ndup:<5}/{ntot:<5} Dup Size:{toh(sdup):<10} (ref:{var.get_ref})"
            if not ndup:
                msg = green(msg)
            elif ndup < C_MAX_FILES and sdup < C_MAX_SIZE:
                msg = blue(msg)
            else:
                msg = red(msg)
            print(msg)

@cli.command('info')
@click.pass_context
@catch_exception
def dupinfo(ctx):
    """
    Return information on var.

    vamtb [-vv] [-f <file pattern> ] info

    """
    file, dir, pattern = get_filepattern(ctx)
    for varfile in search_files_indir(dir, pattern):
        with Var(varfile, dir) as var:
            for zinfo in var.get_zipinfolist:
                print(zinfo)

@cli.command('dbdel')
@click.pass_context
@catch_exception
def dbdel(ctx):
    """
    Remove one var from DB.


    vamtb [-vv] -f file dbdel

    """

    file, dir, pattern = get_filepattern(ctx)
    file or critical("Need a file parameter", doexit=True)
    varfile = VarFile(file, use_db=True)
    if not varfile.exists():
        warn(f"{varfile.file} not found in DB")
    else:
        print(f"Deleting {varfile.file}")
        varfile.db_delete()
        varfile.db_commit()
        info(f"Removed {file} from DB")

@cli.command()
@click.pass_context
@catch_exception
def setref(ctx):
    """
    Set var and files as reference.


    vamtb [-vv] -f file setref

    """
#TODO set noref..
    file, dir, pattern = get_filepattern(ctx)
    file or critical("Need a file parameter", doexit=True)
    for varfile in search_files_indir(dir, pattern):
        with Var(varfile, dir, use_db=True, check_exists=False) as var:
            info(f"Setting var {var} as reference")
            var.db_var_setref(isref=True, files=True)

@cli.command('orig')
@click.pass_context
@catch_exception
def orig(ctx):
    """
    Revert to orig files.


    vamtb [-vv] [-f <file pattern>] orig

    """

    file, dir, pattern = get_filepattern(ctx)
    for mfile in search_files_indir(dir, pattern.replace(".var", ".orig")):
        varfile = mfile.with_suffix(".var")
        debug(f"Restoring {mfile} to {varfile}")
        if varfile.exists():
            os.unlink(varfile)
        os.rename(mfile, varfile)
        with Var(varfile, dir, use_db=True, check_exists=False) as var:
            # If someone corrupted an .orig file
            try:
                var.store_update(confirm=False)
            except Exception as e:
                error(f"Var {var.var} could not be uploaded, error is:\n{e}")

@cli.command('ia')
@click.pass_context
@catch_exception
def ia(ctx):
    """
    Upload var to Internet Archive item.


    vamtb [-vv] [-f <file pattern>] [-a] [-e] [-n] [-i <prefix>] ia

    -a: Do not confirm, always answer yes (will overwrite IA with new content).
    -e: Only update metadata subject.                                         
    -n: Dry-run upload, don't do anything.                                     
    -f: Upload all jpg, not only scene jpgs.                                   
    -c: Only upload CC* license content.                                       
    -i: Change prefix used for the identifier on IA (use only when you are sure the default identifer is already used).

    """

    file, dir, pattern = get_filepattern(ctx)
    n_up = 0
    for varfile in search_files_indir(dir, pattern):
        with Var(varfile, dir, use_db=True) as var:
            if not var.exists():
                info("Skipping")
                continue
            try:
                res = var.ia_upload(
                    meta_only=ctx.obj['meta'], 
                    confirm=not ctx.obj['force'], 
                    verbose=True if ctx.obj['debug_level'] else False, 
                    dry_run=ctx.obj['dryrun'], 
                    full_thumbs=ctx.obj['full'], 
                    only_cc=ctx.obj['cc'], 
                    iaprefix=ctx.obj['iaprefix'])
                if res :
                    info(f"Var {var.var} uploaded successfully to Internet Archive.")
                    n_up += 1
                else:
                    error(f"Var {var.var} was not uploaded to Internet Archive.")
            except Exception as e:
                error(f"Var {var.var} could not be uploaded to Internet Archive., error is:\n{e}")
    print(green(f"{n_up} vars were uploaded"))

@cli.command('anon')
@click.pass_context
@catch_exception
def anon(ctx):
    """
    Upload var to Anonfiles. You need an account overthere.


    vamtb [-vv] [-f <file pattern>] [-n] anon

    -n : Dry-run upload, don't do anything. 

    """

    with open(C_YAML, 'r') as stream:
        conf = yaml.load(stream, Loader=yaml.BaseLoader)
    if 'anon_apikey' not in conf or not conf['anon_apikey']:
        conf['anon_apikey'] = input(blue("Enter Anonfiles apikey ?:"))
        with open(C_YAML, 'w') as outfile:
            yaml.dump(conf, outfile, default_flow_style=False)
        info(f"Stored apikey for future use.")

    file, dir, pattern = get_filepattern(ctx)
    n_up = 0
    for varfile in search_files_indir(dir, pattern):
        with Var(varfile, dir, use_db=True) as var:
            try:
                res = var.anon_upload(apikey = conf['anon_apikey'], dry_run=ctx.obj['dryrun'])
                if res :
                    info(f"Var {var.var} uploaded successfully to anonfiles.")
                    n_up += 1
                else:
                    error(f"Var {var.var} was not uploaded to anonfiles.")
            except Exception as e:
                error(f"Var {var.var} could not be uploaded to anonfiles, error is:\n{e}")
    print(green(f"{n_up} vars were uploaded"))

@cli.command('multiup')
@click.pass_context
@catch_exception
def multiup(ctx):
    """
    Upload var to multiple place.


    vamtb [-vv] [-n] [-f <file pattern>] multiup

    -n : Dry-run upload, don't do anything. 

    """
    for func in (ia, anon):
        ctx.invoke(func)

#TODO add command for morph region /.. editing