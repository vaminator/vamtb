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
  vamtb -d d:\VAM renamevar
  vamtb -d d:\VAM -f ClubJulze.Bangkok.1.var renamevar

  Database:
  vamtb -vvd d:\VAM dbs will scan your vars and create or if modification time is higher, update database
  vamtb -vvd d:\VAM dups will scan your vars and for any files already in a ref var, will reref to use that ref var files
  vamtb -vvd d:\VAM -f sapuzex.Cooking_Lesson.1 dups will reref this var to use external dependencies

Options:
  -d TEXT                 VAM directory.
  -c TEXT                 VAM custom directory.
  -f TEXT                 Var file.
  -v, --verbose           Verbose (twice for debug).  [x>=0]
  -x, --move / --no-move  When checking dependencies move vars with missing
                          dep in 00Dep. When repacking, move files rather than
                          copying
  --help                  Show this message and exit.

Commands:
  autoload      Check vars having autoloading of morph Each morph is then...
  checkdep      Check dependencies of a var
  checkdeps     Check dependencies of all var files.
  checkvars     Check all var files for consistency
  convert       Convert tree to var.
  dbs           Scan vars and store props in db
  dump          Dump var meta.json
  dups          n2 dup find
  multiconvert  Convert directory tree of directory trees to vars.
  printdep      Print dependencies of a var
  renamevar     Rename var from meta.json
  repack        Convert single file to var.
  sortvar       Moves vars to subdirectory named by its creator
  statsvar      Get stats on all vars
  thumb         Gen thumbs from var file(s)

```
