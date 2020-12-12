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
import customdirs

@click.group()
@click.option('dir', '-d', default="D:\\VAM", help='VAM directory.')
@click.option('custom', '-c', default="D:\\VAM", help='VAM custom directory.')
@click.option('file','-f', help='Var file.')
@click.option('-v', '--verbose', count=True, help="Verbose (twice for debug).")
@click.option('-x', '--move/--no-move', default=False, help="When checking dependencies, move vars with missing dep in 00Dep")
@click.pass_context
def cli(ctx, verbose, move, dir, custom, file):
    """ VAM Toolbox

    Examples:
    
    \b
    vamtb -d d:\VAM -vv -f sapuzex.Cooking_Lesson.1 checkdep
    vamtb -d d:\VAM -f ClubJulze.Bangkok.1 printdep
    vamtb -d d:\VAM -f sapuzex.Cooking_Lesson.1 dump
    vamtb -d d:\VAM -f sapuzex.Cooking_Lesson.1 printdep
    vamtb -d d:\VAM -f ClubJulze.Bangkok.1.var thumb
    vamtb -d d:\VAM -v checkdeps
    vamtb -d d:\VAM sortvar  (caution this will reorganize your var directories)
    vamtb -d d:\VAM statsvar
    vamtb -d d:\VAM thumb

    Experimental:
    vamtb -d d:\VAM -c d:\VAM\Saves\scene organize

    """
    logger = logging.getLogger()
    logging.basicConfig(level=("WARNING","INFO","DEBUG")[verbose], format='%(message)s')
    fh = logging.FileHandler('log-vamtb.txt')
    # fh.setLevel(logging.DEBUG)
    logger.addHandler(fh)
    ctx.ensure_object(dict)
    ctx.obj['dir'] = dir
    ctx.obj['custom'] = custom
    ctx.obj['file'] = file
    ctx.obj['move'] = move
    sys.setrecursionlimit(100)  # Vars with a dependency depth of 100 are skipped

@cli.command('organize')
@click.pass_context
def organize(ctx):
    """Organize"""
#    customdirs.organize("Custom/Atom/Person/Morphs", ctx.obj['custom'], ctx.obj['dir'])
    customdirs.organize("Custom/Atom/Person/Hair", ctx.obj['custom'], ctx.obj['dir'])

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
    vars_files = vamdirs.list_vars(dir)
    for var_file in vars_files:
        varfile.split_varname(var_file, dest_dir = "%s/AddonPackages" % dir)

@cli.command('statsvar')
@click.pass_context
def check_vars(ctx):
    """Check all var files for consistency"""
    dir=Path("%s/AddonPackages" % ctx.obj['dir'])
    logging.info("Checking dir %s for vars" % dir)
    all_files = vamdirs.list_vars(dir, pattern="*")
    logging.debug("Found %d files in %s" % (len(all_files), dir))
    for file in all_files:
        varfile.is_namecorrect(file)

@cli.command('statsvar')
@click.pass_context
def stats_vars(ctx):
    """Get stats on all vars"""
    dir=Path("%s/AddonPackages" % ctx.obj['dir'])
    logging.info("Checking stats for dir %s" % dir)
    all_files = vamdirs.list_vars(dir, pattern="*.var")
    creators_file = defaultdict(list)
    for file in all_files:
        creator, _ = file.name.split(".", 1)
        creators_file[creator].append(file.name)
    logging.debug("Found %d files in %s" % (len(all_files), dir))
    for k, v in reversed(sorted(creators_file.items(), key=lambda item: len(item[1]))):
        print("Creator %s has %d files" % (k, len(v)))

@cli.command('checkdeps')
@click.pass_context
def check_deps(ctx):
    """Check dependencies of all var files"""
    dir = Path("%s/AddonPackages" % ctx.obj['dir'])
    move = ctx.obj['move']
    if move:
        movepath=Path(dir, "00Dep")
        Path(movepath).mkdir(parents=True, exist_ok=True)
    else:
        movepath=None
    logging.info(f'Checking deps for vars in {dir}')
    all_vars = vamdirs.list_vars(dir)
    for var in all_vars:
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
    Convert tree to var
    
    """
    # Used for excluding content already packaged and depending on it
    # dir=Path("%s/AddonPackages" % ctx.obj['dir'])
    file=ctx.obj['file']
    custom=ctx.obj['custom']
    logging.debug(f'Converting {custom} to var')

    varfile.make_var(custom, file, outdir="newvar")

    # We might want to move/archive the input_dir to avoid duplicates now
    # TODO

@cli.command('multiconvert')
@click.pass_context
def var_multiconvert(ctx):
    """
    Convert tree of tree to var
    
    """
    custom=ctx.obj['custom']
    logging.debug(f'Converting {custom} to var')

    creatorName = input("Give creator name:")
    for p in Path(custom).glob('*'):
        varfile.make_var(p, None, creatorName=creatorName, packageName=p.name, packageVersion=1, outdir="newvar")


# TODO
# Remove old versions of var
# Find vars autoloading morphs and shouldn't

@cli.command('autoload')
@click.pass_context
def autoload(ctx):
    """Check vars having autoloading of morph"""
    dir=Path("%s/AddonPackages" % ctx.obj['dir'])
    vars_files = vamdirs.list_vars(dir)
    for var_file in vars_files:
        json = varfile.extract_meta_var(var_file)
        if 'customOptions' in json and json['customOptions']['preloadMorphs'] != "false":
            print(f"{var_file} has autoloading")


"""
Convert dirstruct/zip to var
Parse dirstruct/zip of scene and for each corresponding 
List content of var : so that the user can decide to select a few things

"""
#def repack(ctx):


if __name__ == '__main__':
    cli() # pylint: disable=no-value-for-parameter

