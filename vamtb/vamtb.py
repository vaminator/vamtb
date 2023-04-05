import os
import sys
import yaml
import zlib
import click
import shutil
from collections import defaultdict
from pathlib import Path
from tqdm import tqdm
#import PySimpleGUI as sg

from vamtb.graph import Graph
from vamtb.var import Var
from vamtb.file import FileName
from vamtb.vamex import *
from vamtb.log import *
from vamtb.utils import *
from vamtb.varfile import VarFile
from vamtb.db import Dbs
from vamtb.profile import ProfileMgr

@click.group()
@click.option('-a', '--force/--no-force', default=False,        help="Do not ask for confirmation.")
@click.option('-b', '--usedb/--no-usedb', default=False,        help="Use DB.")
@click.option('-c', '--cc/--no-cc', default=False,              help="Only upload CC license content")
@click.option('dir', '-d',                                      help='Use a specific VAM directory.')
@click.option('-e', '--meta/--no-meta', default=False,          help="Only reset subject metadata.")
@click.option('file','-f',                                      help='Var file to act on.')
@click.option('inp', '-g',                                      help='Input directory for var creation.')
@click.option('iaprefix','-i',                                  help=f'Internet Archive identifier prefix (defaults to {IA_IDENTIFIER_PREFIX}).')
@click.option('-j', '--optimize', count=True,                   help="Image Optimize level (none:No png to jpg that is lossless, 1: Jpeg qual 90%, 2: Jpeg qual 75%).")
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
def cli(ctx, verbose, inp, optimize, move, ref, usedb, dir, file, dup, remove, setref, force, meta, progress, dryrun, full, cc, iaprefix):
    # pylint: disable=anomalous-backslash-in-string
    """
    For specific command help use vamtb <command> --help

    For file pattern OPTION, you need to pass a regular expression like .*\.var (* can be replaced by %)
    """

    log_setlevel(verbose)
    info("Welcome to vamtb")

    ctx.ensure_object(dict)
    ctx.obj['file']        = file
    ctx.obj['move']        = move
    ctx.obj['ref']         = ref
    ctx.obj['usedb']       = usedb
    ctx.obj['debug_level'] = verbose
    ctx.obj['optimize']    = optimize
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
    ctx.obj['inp']         = inp
    conf = {}

    global C_YAML

    if not dir:
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
    else:
        dir = Path(dir)

    if dir.stem != "AddonPackages":
        dir = dir / "AddonPackages"

    if not ( dir.is_dir() and dir.exists() ):
        critical(f"AddonPackages '{dir}' is not existing directory")

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
        with Var(varfile, dir) as var:
            depvarfiles = sorted(var.dep_frommeta(), key=str.casefold)
            print(f">Printing dependencies for {green(var.var):<50} : {len(depvarfiles) if len(depvarfiles) else 'No'} dependencies")
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

    Not recursive

    -m: print as json

    """
    file, dir, pattern = get_filepattern(ctx)
    json = ctx.obj['move']
    for varfile in search_files_indir(dir, pattern):
        with Var(varfile, dir) as var:
            deps = list(set(var.dep_fromfiles()))
            depvarfiles = sorted(deps, key=str.casefold)
            print(f">Printing real dependencies for {green(var.var):<50} : {len(depvarfiles) if len(depvarfiles) else 'No'} dependencies")
            for depvarfile in depvarfiles:
                #var.license
                xvar = VarFile(depvarfile).var_nov
                try:
                    with Var(depvarfile, dir, use_db=True) as dvar:
                        xlicense = Var(dvar.latest(), dir, use_db=True).license
                except VarNotFound:
                    #print(f"Didnt find {depvarfile}")
                    xlicense="Questionable"
                if json:
                    s=( f'"{xvar}.latest":{{\n'
                        f'    "licenseType" : "{xlicense}",\n'
                        '    "dependencies" : {}\n'
                        '},'
                    )
                    print(s)
                else:
                    mess = green("Found")
                    try:
                        _ = Var(depvarfile, dir)
                    except VarNotFound:
                        mess = red("Not found")
                    else:
                        mess = green("Found")
                    print(f"{depvarfile:<68}: {xlicense:<16} {mess}")

@cli.command('dumpvar')
@click.pass_context
@catch_exception
def dumpvar(ctx):
    """Dump meta.json from var.


    vamtb [-vv] -f <file pattern> dumpvar
    
    """
    file, dir, pattern = get_filepattern(ctx)
    file or critical("Need a file parameter")
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
    file or critical("Need a file parameter")
    with Var(file, dir) as var:
        var.remroot()

@cli.command('sortvar')
@click.pass_context
@catch_exception
def sortvars(ctx):
    """Moves vars to subdirectory named by its creator.


    vamtb [-vv] [-f <file pattern> ] sortvar
    
    Crc is checked before erasing duplicates"""

    file, dir, pattern = get_filepattern(ctx)
    info(f"Sorting var in {dir}")
    for file in search_files_indir(dir, pattern):
        try:
            with Var(file, dir) as var:
                warn(f"Moving var {var}")
                var.move_creator()
        except zlib.error:
            error(f"Zip error on var {file}")

@cli.command('checkvar')
@click.pass_context
@catch_exception
def checkvar(ctx):
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
                info(f">Checking {green(var.var):<50}")
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
def statsvars(ctx):
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

    When using -b, don't use database but rather file system.

    You can redo the same dependency check later by moving back the directory and correct vars will be moved out of this directory if they are now valid.
    """
    # FIXME DOC even with database mode, the file system is still used (grepping in files..)
    move = ctx.obj['move']
    usedb = ctx.obj['usedb']

    file, dir, pattern = get_filepattern(ctx)
    if move:
        full_bad_dir = Path(dir) / C_BAD_DIR
        full_bad_dir.mkdir(parents=True, exist_ok=True)
    stop = True if move else False

    for mfile in sorted(search_files_indir(dir, pattern)):
        try:
            with Var(mfile, dir, use_db=not usedb) as var:
                print(f">Checking dependencies of {green(var.var):<50}")
                try:
                    if not usedb:
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
            info(f"Scanning {var}")
            try:
                if var.store_update(confirm=False if ctx.obj['force'] else True):
                    stored += 1
            except VarMalformed as e:
                error(f"Var {var.var} malformed")
            except NoMetaJson:
                error(f"Var {var.var} malformed (no meta found)")
            except VarMetaJson as e:
                error(f"Var {var.var} has something wrong in meta: {e}")

    info(f"{stored} var files stored")


@cli.command('dbclean')
@click.pass_context
def dbclean(ctx):
    """
    Remove vars from DB which are not found on disk.

    vamtb [-vv] [-a] [-c] dbclean

    -a: Delete without prompting

    -c: Only list missing files, don't do anything.
    """
    nmiss = 0
    files = search_files_indir(ctx.obj['dir'], f".*\.var", ign=True)
    varnames = set([ e.with_suffix("").name for e in files ])
    dbvars = set(Dbs.get_vars())
    diff = sorted(list(varnames - dbvars) + list(dbvars - varnames), key=str.casefold)
    for var in diff:
        if var not in dbvars:
            continue
        print(f"Var {red(var)} is in DB but not on disk  ")
        nmiss = nmiss + 1
        if ctx.obj['cc']:
            continue
        if ctx.obj['force'] or input("Delete from DB: Y [N] ?").upper() == "Y":
            varfile = VarFile(var, use_db=True)
            print(f"Deleting {varfile.file}")
            varfile.db_delete()
            varfile.db_commit()
            info(f"Removed {var} from DB")
    print(f"{nmiss} files missing")

@cli.command('graph')
@click.pass_context
@catch_exception
def graph(ctx):
    """
    Generate graph of deps, one per var.

    vamtb [-a] [-vv] [-f <file pattern> ] graph

    -a: Generate png rather than pdf

    """
    if shutil.which(C_DOT) is None:
        critical(f"Make sure you have graphviz installed in {C_DOT}.")

    file, dir, pattern = get_filepattern(ctx)
    for varfile in search_files_indir(dir, pattern):
        with Var(varfile, dir, use_db=True) as var:
            info(f"Calculating dependency graph for {var.var}")
            Graph.dotty(var, ext="png" if ctx.obj['force'] else "pdf")

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
    critical("Be cautious with what you accept (Y). If some bundled content was modified, you might get some split content.", doexit=False)
    critical("Also vars referencing this content will have broken dependencies. Check that manually for now.", doexit=False)
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

@cli.command('imageopt')
@click.pass_context
@catch_exception
def imageopt(ctx):
    """
    Optimize images in vars.


    vamtb [-jj] [-f <file pattern> ] imageopt

    Without option: no loss of quality, just optimize png

    -j:             same but convert png to jpg of qual 90%

    -jj:            same but convert png to jpg of qual 75%
    """
    oldsz = 0
    opt_level = ctx.obj['optimize']
    file, dir, pattern = get_filepattern(ctx)
    for varfile in search_files_indir(dir, pattern):
        with Var(varfile, dir, use_db=True) as var:
            msg = f"Image optimisation on {varfile.name:<100} size:"
            if not var.exists():
                print(red(f"{msg} UNKNOWN"))
                continue
            oldsz = var.size
            print(green(f"{msg} {toh(var.size)}"))
            if var.exists():
                res = var.var_opt_images(opt_level)
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

@cli.command('zinfo')
@click.pass_context
@catch_exception
def zinfo(ctx):
    """
    Return zip meta info of files in var.

    vamtb [-vv] [-f <file pattern> ] zinfo

    """
    file, dir, pattern = get_filepattern(ctx)
    for varfile in search_files_indir(dir, pattern):
        with Var(varfile, dir) as var:
            for zinfo in var.get_zipinfolist:
                print(f"{zinfo.filename}, Compress={zinfo.compress_type}, FSize={zinfo.file_size}, CSize={zinfo.compress_size}")

@cli.command('dbdel')
@click.pass_context
@catch_exception
def dbdel(ctx):
    """
    Remove one var from DB.


    vamtb [-vv] -f file dbdel

    """

    file, dir, pattern = get_filepattern(ctx)
    file or critical("Need a file parameter")
    varfile = VarFile(file, use_db=True)
    if not varfile.exists():
        warn(f"{varfile.file} not found in DB")
    else:
        print(f"Deleting {varfile.file}")
        varfile.db_delete()
        varfile.db_commit()
        info(f"Removed {file} from DB")

@cli.command('setref')
@click.pass_context
@catch_exception
def setref(ctx):
    """
    Set var and files as reference.


    vamtb [-vv] -f file setref

    """
#TODO set noref..
    file, dir, pattern = get_filepattern(ctx)
    file or critical("Need a file parameter")
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
                    verbose=True, 
                    dry_run=ctx.obj['dryrun'], 
                    full_thumbs=ctx.obj['full'], 
                    only_cc=ctx.obj['cc'], 
                    iaprefix=ctx.obj['iaprefix'])
                if res :
                    info(f"Var {var.var} uploaded successfully to Internet Archive.")
                    n_up += 1
                else:
                    info(f"Var {var.var} was not uploaded to Internet Archive.")
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
    if not conf.get('anon_apikey', False):
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

@cli.command('link')
@click.pass_context
@catch_exception
def link(ctx):
    """
    Link var and dependent to configured directory.


    vamtb [-vv] [-f <file pattern> ] [-m] link

    -m : Don't recurse dependencies.

    -z : Use configured linked dir in config file for destination directory (otherwise uses current dir)

    -f : When using configured linked dir, don't confirm destination directory.

    """
    ddir = ""

    def linkfile(mvar):
        srcfile = mvar.path
        basefile = os.path.basename(srcfile)
        linkdir = ddir
        if not os.path.islink(f"{linkdir}/{basefile}"):
            try:
                info(f"{linkdir}/{basefile}  ->  {srcfile}")
                os.symlink(f"{srcfile}", f"{linkdir}/{basefile}")
            except FileExistsError:
                warn(f"ERROR exists {linkdir}/{basefile}")

    conf = {}
    writeconf = False
    file, dir, pattern = get_filepattern(ctx)

    if conf.get('setref', False):
        with open(C_YAML, 'r') as stream:
            conf = yaml.load(stream, Loader=yaml.BaseLoader)
            if 'linkdir' not in conf or \
                (not ctx.obj['force'] and input(red(f"Link to {conf['linkdir']} ? [Y]N")).upper() == "N") :
                writeconf = True
        dir = Path(conf['dir'])

        if writeconf:
            conf['linkdir'] = input(blue("Where to link to ?:"))
            with open(C_YAML, 'w+') as stream:
                yaml.dump(conf, stream, default_flow_style=False)
                info(f"Configured {conf['linkdir']} in {C_YAML}")
            ddir = conf['linkdir']
    else:
        ddir = os.getcwd()

    for varfile in search_files_indir2(dir, pattern):
        etarget = Path(ddir, os.path.basename(varfile))
        if etarget.exists() and etarget.is_file():
            info(f"{etarget} already exists")
        with Var(varfile, dir, use_db=True) as var:
            warn(f"Linking {var} {'' if ctx.obj['move'] else 'and dependencies'}")
            linkfile(var)
            if not ctx.obj['move']:
                var.rec_dep(stop=False, dir=dir, func = linkfile)


@cli.command('latest')
@click.pass_context
@catch_exception
def latest(ctx):
    """
    Show "latest" version of var as an absolute filename

    vamtb [-vv] -f pattern latest

    pattern is creator.asset[.version]
    """
    if not ctx.obj['file']:
        critical("Need a file name")

    file, dir, pattern = get_filepattern(ctx)

    try:
        creator, asset, _ = ctx.obj['file'].split('.', 3)
    except ValueError:
        creator, asset = ctx.obj['file'].split('.', 2)

    ln = f"{creator}.{asset}.latest"
    with Var(ln, dir, use_db=True) as latest:
        print(f"{latest.path}")

@cli.command('profile')
@click.pass_context
@catch_exception
def profile(ctx):
    """
    Creates or selects a new VaM installation instance.

    vamtb [-vv] profile

    User is requested which directories should be used.

    All profiles lie in a user defined directory, each in a subdirectory

    A special profile called Full will be created if doesn't exists:

      --> has empty Custom/ Saves/ etc.. directories

      User needs to customize to share plugindata, etc..

      --> has AddonPackages being a softlink to your vars directory

    Other profiles have:


      --> Custom/ Saves/ directories linked to Full directories

      --> AddonPackages is a directory containing links to your vars directory

      Use vamtb link command to add more

    """
    with open(C_YAML, 'r') as stream:
        conf = yaml.load(stream, Loader=yaml.BaseLoader)
    if 'multidir' not in conf:
        conf['multidir'] = input("Directory where profiles are/will be located:")
        if not Path(conf['multidir']).is_dir():
            critical(f"{conf['multidir']} is not an existing directory. Please create manually.")
        with open(C_YAML, 'w+') as stream:
            yaml.dump(conf, stream, default_flow_style=False)
            info(f"Configured {conf['multidir']} in {C_YAML}")
    if 'exedir' not in conf:
        conf['exedir'] = input("Directory where vam exe is:")
        if not Path(conf['exedir'], "VaM.exe").is_file():
            critical(f"Could not find {conf['exedir']}/VaM.exe")
        with open(C_YAML, 'w+') as stream:
            yaml.dump(conf, stream, default_flow_style=False)
            info(f"Configured {conf['exedir']} in {C_YAML}")
    if 'cachedir' not in conf:
        conf['cachedir'] = input("Directory where caches will be (one cache directory per profile):")
        if not Path(conf['cachedir']).is_dir():
            critical(f"{conf['cachedir']} is not an existing directory.")
        with open(C_YAML, 'w+') as stream:
            yaml.dump(conf, stream, default_flow_style=False)
            info(f"Configured {conf['cachedir']} in {C_YAML}")
    if 'refvars' not in conf:
        print("We did not find reference vars (vars you want to always have for new profiles)")
        print("We will initialize a default list. Please edit vamtb.yml to suite your needs")
        conf['refvars'] = C_REF_VARS
        with open(C_YAML, 'w+') as stream:
            yaml.dump(conf, stream, default_flow_style=False)
            info(f"Configured refvars in {C_YAML}")

    profmgr = ProfileMgr(conf['multidir'], conf['exedir'], conf['cachedir'], conf['dir'], conf['refvars'])
    adirs = next(os.walk(conf['multidir']))[1]
    for i, d in enumerate(adirs):
        print(f"{i} : {d}")

    if "Full" not in adirs:
        print("First we need to create the Full profile: AddonPackages links to your vam installation") 
        profmgr.new("Full")
        print("Profile Full initialized, you can now run the tool again to create a personal profile")
        exit(0)
    answer = input("Choose Profile [N for new profile]: ")

    if answer.upper() == "N":
        profmgr.new()
    else:
        adir = adirs[int(answer)]
        profmgr.select(adir)

@cli.command('renamevar')
@click.pass_context
@catch_exception
def renamevar(ctx):
    """
    Rename file to var getting props from meta.json.


    vamtb [-vv] [-p] -f file renamevar

    -p : request password

    Var version will be set to 1

    """

    if not ctx.obj['file']:
        critical("Need a file name")

    with Var(ctx.obj['file'], check_exists=False, check_naming=False) as mvar:
        if ctx.obj['progress']:
            password = input("Password:")
            mvar.set_password(password)
        js = mvar.meta()
        rcreator, rasset = js['creatorName'],js['packageName']

    try:
        creator, asset, version, _ = mvar.path.name.split('.', 4)
    except ValueError:
        creator = ""
        asset = ""
        version = 1
    if creator.replace(" ", "_") != rcreator.replace(" ", "_") or asset.replace(" ", "_") != rasset.replace(" ", "_"):
            rfile = mvar.path.parents[0] / f"{rcreator}.{rasset}.{version}.var".replace(" ", "_")
            print(f"Renaming {mvar.path} to {rfile}")
            os.rename(mvar.path, rfile)


@cli.command('rdep')
@click.pass_context
@catch_exception
def rdep(ctx):
    """
    Reverse depends of vars.


    vamtb [-vv] [-f file] rdep

    """

    file, dir, pattern = get_filepattern(ctx)

    for varfile in search_files_indir2(dir, pattern):
        with Var(varfile, dir, use_db=True, check_exists=False, check_file_exists=False, check_naming=True) as var:
            rvars = var.get_rdep()
            print (green(f"Reverse depends {var.var}: ") + ','.join(rvars))

@cli.command('nordep')
@click.pass_context
@catch_exception
def nordep(ctx):
    """
    Prints all var which don't have a reverse dependent.


    vamtb [-vv] [-f pattern] nordep

    """

    file, dir, pattern = get_filepattern(ctx)

    for varfile in search_files_indir2(dir, pattern):
        with Var(varfile, dir, use_db=True, check_exists=False, check_file_exists=False, check_naming=True) as var:
            rvars = var.get_rdep()
            if not rvars:
                msg = f"No var depends on {var.var}"
                if var.db_files(pattern='/scene/') or var.db_files(pattern='/Clothing/') or var.db_files('/Assets/'):
                    msg = green(msg)
                else:
                    msg = red(msg)
                print (msg)
            else:
                info(f"{var.var} : {len(rvars)} vars depending on it:{rvars}")

@cli.command('dep')
@click.pass_context
@catch_exception
def dep(ctx):
    """
    Depends of a var.


    vamtb [-vv] -f file dep

    """

    if not ctx.obj['file']:
        critical("Need a file name")

    file, dir, pattern = get_filepattern(ctx)

    for varfile in search_files_indir2(dir, pattern):
        with Var(varfile, dir, use_db=True, check_exists=False, check_file_exists=False, check_naming=True) as var:
            rvars = var.get_dep()
            print (green(f"Depends of {var.var}: ") + ','.join(rvars))



# @cli.command('gui')
# @click.pass_context
# @catch_exception
# def gui(ctx):
#     """
#     There's no graphical user interface
#     """
#     # First the window layout in 2 columns

#     buttons_column = [
#         [ sg.Button("Meta", key="-META-") ],
#         [ sg.Button("Dep", key="-DEP-") ],
#         [ sg.Button("Rdep", key="-RDEP-") ],
#     ]

#     file_list_column = [
#         [
#             sg.Listbox(
#                 values=[], enable_events=True, size=(40, 40), key="-FILE LIST-"
#             )
#         ],
#     ]


#     # For now will only show the name of the file that was chosen

#     image_viewer_column = [
#         [sg.Text(key="-IMAGE-")],
#     ]

#     # ----- Full layout -----
#     layout = [
#         [
#             [
#                 sg.Text("AddonPackages Folder"),
#                 sg.In(enable_events=True, visible=False, key="-FOLDER-"),
#                 sg.FolderBrowse(),
#                 sg.Text(size=(40, 1), key="-TOUT-", justification="right"),
#             ],
#             sg.Column(buttons_column),
#             sg.Column(file_list_column),
#             sg.VSeperator(),
#             sg.Column(image_viewer_column),
#         ]
#     ]

#     window = sg.Window("Vam Tool Box", layout, resizable=True, finalize=True, location=(0,0))
    
#     folder = ctx.obj['dir']
#     fnames = files_in_dir(folder)    
#     window["-FILE LIST-"].update(fnames)

#     # Run the Event Loop
#     while True:
#         event, values = window.read()
#         if event == "Exit" or event == sg.WIN_CLOSED:
#             break
#         # Folder name was filled in, make a list of files in the folder
#         if event == "-FOLDER-":
#             folder = values["-FOLDER-"]

#             fnames = files_in_dir(folder)
#             window["-FILE LIST-"].update(fnames)

#         elif event == "-FILE LIST-":  # A file was chosen from the listbox
#             try:
#                 window["-TOUT-"].update(values["-FILE LIST-"][0])
# #                window["-IMAGE-"].update(text=filename)
#             except:
#                 pass
#         elif event == "-META-":
#             with Var(values["-FILE LIST-"][0], folder) as var:
#                 window["-IMAGE-"].update(prettyjson(var.load_json_file("meta.json")) )
#         elif event == "-DEP-":
#             with Var(values["-FILE LIST-"][0], folder, use_db=True) as var:
#                 deps = var.get_dep()
#             window["-IMAGE-"].update("\n".join(deps) )
#         elif event == "-RDEP-":
#             with Var(values["-FILE LIST-"][0], folder, use_db=True) as var:
#                 rdeps = var.get_rdep()
#             window["-IMAGE-"].update("\n".join(rdeps) )
             
#     window.close()
#TODO add command for morph region /.. editing