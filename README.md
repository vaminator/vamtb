# vamtb
Vam toolbox

You can use already built binaries (see Releases, not built often though)

It's also possible to build from source and install:
````
python setup.py install
````

To run it under windows, you should force UTF8 for international characters handling on the console:

````
python -X utf8 vamtb.py <rest of options>
````

```text
Usage: vamtb.py [OPTIONS] COMMAND [ARGS]...

  VAM Toolbox

  Dependency handling:
  vamtb -d d:\VAM -v checkdeps
  vamtb -d d:\VAM -vv -f sapuzex.Cooking_Lesson.1 checkdep
  vamtb -d d:\VAM -f ClubJulze.Bangkok.1 printdep
  vamtb -d d:\VAM -f ClubJulze.Bangkok.1 printrealdep

  Meta json handling:
  vamtb -d d:\VAM -f sapuzex.Cooking_Lesson.1 dump

  Thumb handling:
  vamtb -d d:\VAM thumb
  vamtb -d d:\VAM -f ClubJulze.Bangkok.1.var thumb

  Organizing:
  vamtb -d d:\VAM sortvar  (caution this will reorganize your var directories with <creator>/*)
  vamtb -d d:\VAM statsvar

  Building:
  vamtb -vvc d:\ToImport\SuperScene convert
  vamtb -x repack
  vamtb -d d:\VAM renamevar (caution this will rename vars based on meta.json creator and creation name)
  vamtb -d d:\VAM -f ClubJulze.Bangkok.1.var renamevar
  vamtb -d d:\VAM -f Community.PosePack.1 noroot (caution this will remove root node from pose, don't do this on scenes)

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
  noroot        Remove root node stored in pose presets
  printdep      Print dependencies of a var from reading meta.
  printrealdep  Print dependencies of a var from inspecting all json files.
  renamevar     Rename var from meta.json
  repack        Convert single file to var.
  sortvar       Moves vars to subdirectory named by its creator
  statsvar      Get stats on all vars
  thumb         Gen thumbs from var file(s)

```
When using dbs, this will generate a sqlite file that you can browse you vars and included files insude with any tool compatible, like https://sqlitebrowser.org/