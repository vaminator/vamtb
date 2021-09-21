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
  vamtb -d d:\VAM sortvar  Reorganize your var directories with <creator>/*
            If a file already exists in that directory, CRC is checked before overwritting.
  vamtb -d d:\VAM statsvar will dump some statistics

  Building:
  vamtb -vvc d:\ToImport\SuperScene convert
  vamtb -x repack
  vamtb -d d:\VAM renamevar (caution this will rename vars based on meta.json creator and creation name)
  vamtb -d d:\VAM -f ClubJulze.Bangkok.1.var renamevar
  vamtb -d d:\VAM -f Community.PosePack.1 noroot  - Remove root node from poses (caution this will remove root node from pose, don't do this on scenes)
  vamtb -d d:\VAM -f Community.PosePack.1 uiap - Will generate uiap file containing pose presets, you then merge that to existing uiap

  Database:
  vamtb -vvd d:\VAM dbs will scan your vars and create or if modification time is higher, update database
  vamtb -vvd d:\VAM dotty will graph your collection
  vamtb -vvd d:\VAM -f sapuzex.Cooking_Lesson.1 dotty will graph this var
  vamtb -vvd d:\VAM dottys will graph each var seperately

  Character encoding on windows:
  On windows cmd will use cp1252 so you might get some errors displaying international characters.
  Start vamtb with python -X utf8 vamtb.py <rest of parameters>

Options:
  -d TEXT                 VAM directory (default cur dir).
  -c TEXT                 VAM custom directory.
  -f TEXT                 Var file.
  -v, --verbose           Verbose (twice for debug).  [x>=0]
  -x, --move / --no-move  When checking dependencies move vars with missing
                          dep in 00Dep. When repacking, move files rather than
                          copying
  --help                  Show this message and exit.

Commands:
  autoload      Check vars having autoloading of morph
  checkdep      Check dependencies of a var
  checkdeps     Check dependencies of all var files.
  checkvars     Check all var files for consistency
  convert       Convert tree to var.
  dbs           Scan vars and store props in db
  dotty         Gen dot graph of deps
  dottys        Gen dot graph of deps, one per var
  dump          Dump var meta.json
  multiconvert  Convert directory tree of directory trees to vars.
  noroot        Remove root node stored in pose presets
  printdep      Print dependencies of a var from reading meta.
  printrealdep  Print dependencies of a var from inspecting all json files.
  renamevar     Rename var from meta.json
  repack        Convert single file to var.
  sortvar       Moves vars to subdirectory named by its creator
  statsvar      Get stats on all vars
  thumb         Gen thumbs from var file(s)
  uiap          Gen uia preset from var

```
When using dbs subcommand, this will generate a sqlite file that you can browse you vars and included files insude with any tool compatible, like [sqlitebrowser](https://sqlitebrowser.org/).

For dotty subcommand to work, you will need dot from [graphiz](https://www.graphviz.org/download/) installed in c:\Graphviz\bin\dot.exe