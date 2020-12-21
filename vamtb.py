import logging
import os
import pprint
import sys
from collections import defaultdict
from pathlib import Path
import vamex
import click
import vamdirs
import varfile
import shutil

@click.group()
@click.option('dir', '-d', default="D:\\VAM", help='VAM directory.')
@click.option('custom', '-c', default="D:\\VAM", help='VAM custom directory.')
@click.option('file','-f', help='Var file.')
@click.option('-v', '--verbose', count=True, help="Verbose (twice for debug).")
@click.option('-x', '--move/--no-move', default=False, help="When checking dependencies move vars with missing dep in 00Dep. When repacking, move files rather than copying")
@click.pass_context
def cli(ctx, verbose, move, dir, custom, file):
    # pylint: disable=anomalous-backslash-in-string
    """ VAM Toolbox

    \b
    Dependency handling:
    vamtb -d d:\VAM -vv -f sapuzex.Cooking_Lesson.1 checkdep
    vamtb -d d:\VAM -f ClubJulze.Bangkok.1 printdep
    vamtb -d d:\VAM -v checkdeps
    \b
    Meta json handling:
    vamtb -d d:\VAM -f sapuzex.Cooking_Lesson.1 dump
    \b
    Thumb handling:
    vamtb -d d:\VAM -f ClubJulze.Bangkok.1.var thumb
    vamtb -d d:\VAM thumb
    \b
    Organizing:
    vamtb -d d:\VAM sortvar  (caution this will reorganize your var directories with <creator>/*)
    vamtb -d d:\VAM statsvar
    \b
    Building:
    vamtb -vvc d:\ToImport\SuperScene convert
    vamtb -x repack
    """
    logger = logging.getLogger()
    logging.basicConfig(level=("WARNING","INFO","DEBUG")[verbose], format='%(message)s')
    fh = logging.FileHandler('log-vamtb.txt', mode="w")
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    # fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    ctx.ensure_object(dict)
    ctx.obj['dir'] = dir
    ctx.obj['custom'] = custom
    ctx.obj['file'] = file
    ctx.obj['move'] = move
    sys.setrecursionlimit(100)  # Vars with a dependency depth of 100 are skipped

@cli.command('printdep')
@click.pass_context
def printdep(ctx):
    """Print dependencies of a var"""
    vamdirs.recurse_dep("%s/AddonPackages" % ctx.obj['dir'], ctx.obj['file'], do_print = True)

@cli.command('checkdep')
@click.pass_context
def checkdep(ctx):
    """Check dependencies of a var"""
    vamdirs.recurse_dep("%s/AddonPackages" % ctx.obj['dir'], ctx.obj['file'], do_print = False)

@cli.command('dump')
@click.pass_context
def dumpvar(ctx):
    """Dump var meta.json"""
    pp = pprint.PrettyPrinter(indent=4)
    try:
        pp.pprint(varfile.extract_meta_var(vamdirs.find_var(ctx.obj['dir'],ctx.obj['file'])))
    except vamex.VarNotFound as e:
        logging.error(f"Couldn't find var: {e}")
    except Exception as e:
        logging.error(f"Couldn't dump var: {e}")

@cli.command('sortvar')
@click.pass_context
def sort_vars(ctx):
    """Moves vars to subdirectory named by its creator"""
    dir=ctx.obj['dir']
    logging.info("Sorting var in %s" % dir)
    all_files = vamdirs.list_vars(dir, pattern="*")
    vars_files = vamdirs.list_vars(dir)
    mdir=Path("%s/AddonPackages" % ctx.obj['dir'])
    if not mdir.exists():
        mdir=Path(ctx.obj['dir'])
    for var_file in vars_files:
        try:
            varfile.is_namecorrect(var_file)
        except vamex.VarNameNotCorrect:
            logging.error(f"File {var_file} has incorrect naming.")
            continue
        try:
            varfile.extract_meta_var(var_file)
        except vamex.VarMetaJson as e:
            logging.error(f"File {var_file} is corrupted [{e}].")
            continue
        varfile.split_varname(var_file, dest_dir = mdir)
        jpg = varfile.find_same_jpg(all_files, var_file)
        if jpg:
            varfile.split_varname(jpg[0], dest_dir = mdir)

@cli.command('statsvar')
@click.pass_context
def check_vars(ctx):
    """Check all var files for consistency"""
    mdir=Path("%s/AddonPackages" % ctx.obj['dir'])
    if not mdir.exists():
        mdir=Path(ctx.obj['dir'])
    logging.info("Checking dir %s for vars" % dir)
    all_files = vamdirs.list_vars(mdir, pattern="*")
    logging.debug("Found %d files in %s" % (len(all_files), mdir))
    for file in all_files:
        varfile.is_namecorrect(file)

@cli.command('statsvar')
@click.pass_context
def stats_vars(ctx):
    """Get stats on all vars"""
    mdir=Path("%s/AddonPackages" % ctx.obj['dir'])
    if not mdir.exists():
        mdir=Path(ctx.obj['dir'])
    logging.info("Checking stats for dir %s" % mdir)
    all_files = vamdirs.list_vars(dir, pattern="*.var")
    creators_file = defaultdict(list)
    for file in all_files:
        creator, _ = file.name.split(".", 1)
        creators_file[creator].append(file.name)
    logging.debug("Found %d files in %s" % (len(all_files), mdir))
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
    dir = Path("%s/AddonPackages" % ctx.obj['dir'])
    move = ctx.obj['move']
    if move:
        movepath=Path(dir, "00Dep")
        Path(movepath).mkdir(parents=True, exist_ok=True)
    else:
        movepath=None
    logging.info(f'Checking deps for vars in {dir}')
    all_vars = vamdirs.list_vars(dir)
    for var in sorted(all_vars):
        try:
            vamdirs.recurse_dep(dir, var.with_suffix('').name, do_print= False, movepath=movepath)
        except (vamex.VarNotFound, vamex.VarNameNotCorrect, vamex.VarMetaJson, vamex.VarExtNotCorrect, vamex.VarVersionNotCorrect) as e:
            logging.error(f'While handing var {var.name}, we got {type(e).__name__} {e}')
            if movepath:
                Path(var).rename(Path(movepath, var.name))
        except Exception as e:
            logging.error(f'While handing var {var.name}, caught exception {e}')
            raise

@cli.command('thumb')
@click.pass_context
def vars_thumb(ctx):
    """Gen thumbs from var file(s)"""
    basedir="thumb"
    mdir=Path("%s/AddonPackages" % ctx.obj['dir'])
    if not mdir.exists():
        mdir=Path(ctx.obj['dir'])
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
    """Check vars having autoloading of morph"""
    mdir=Path("%s/AddonPackages" % ctx.obj['dir'])
    if not mdir.exists():
        mdir=Path(ctx.obj['dir'])
    vars_files = vamdirs.list_vars(dir)
    for var_file in vars_files:
        json = varfile.extract_meta_var(var_file)
        if 'customOptions' in json and json['customOptions']['preloadMorphs'] != "false":
            print(f"{var_file} has autoloading")

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
    creatorName = input("Give creator name:")

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

if __name__ == '__main__':
    cli() # pylint: disable=no-value-for-parameter

