# vamtb
Vam toolbox

You can use already built binaries (see Releases)

It's also possible to build from source and install:
````
python setup.py install
````

```text
Usage: vamtb.py [OPTIONS] COMMAND [ARGS]...

  VAM Toolbox

  Dependency handling:
  vamtb -d d:\VAM -vv -f sapuzex.Cooking_Lesson.1 checkdep
  vamtb -d d:\VAM -f ClubJulze.Bangkok.1 printdep
  vamtb -d d:\VAM -v checkdeps

  Meta json handling:
  vamtb -d d:\VAM -f sapuzex.Cooking_Lesson.1 dump

  Thumb handling:
  vamtb -d d:\VAM -f ClubJulze.Bangkok.1.var thumb
  vamtb -d d:\VAM thumb

  Organizing:
  vamtb -d d:\VAM sortvar  (caution this will reorganize your var directories with <creator>/*)
  vamtb -d d:\VAM statsvar

  Building:
  vamtb -vvc d:\ToImport\SuperScene convert
  vamtb -x repack

Options:
  -d TEXT                 VAM directory.
  -c TEXT                 VAM custom directory.
  -f TEXT                 Var file.
  -v, --verbose           Verbose (twice for debug).
  -x, --move / --no-move  When checking dependencies move vars with missing
                          dep in 00Dep. When repacking, move files rather than
                          copying

  --help                  Show this message and exit.

Commands:
  autoload      Check vars having autoloading of morph
  checkdep      Check dependencies of a var
  checkdeps     Check dependencies of all var files.
  convert       Convert tree to var.
  dump          Dump var meta.json
  multiconvert  Convert directory tree of directory trees to vars.
  printdep      Print dependencies of a var
  repack        Convert single file to var.
  sortvar       Moves vars to subdirectory named by its creator
  statsvar      Get stats on all vars
  thumb         Gen thumbs from var file(s)

```
