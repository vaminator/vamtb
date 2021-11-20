# VamTB

-- VamToolBox --

## Install
Build from source and install dependencies:
````
python setup.py install
````

## Usage
Open windows terminal (rather than cmd.exe) and run the batch file:
```
vtb --help
```
To interrupt, hit twice ctrl-c.

Calling it with python:
````
python -X utf8 vamtb.py <rest of options>
````

## Options
```text
Usage: vamtb.py [OPTIONS] COMMAND [ARGS]...

  VAM Toolbox

  Dependency handling (from disk)
  vamtb -d d:\VAM -v checkdeps
  vamtb -d d:\VAM -vv -f sapuzex.Cooking_Lesson.1 checkdep
  vamtb -d d:\VAM -f ClubJulze.Bangkok.1 printdep
  vamtb -d d:\VAM -f ClubJulze.Bangkok.1 printrealdep

  Meta json handling (from disk)
  vamtb -d d:\VAM -f sapuzex.Cooking_Lesson.1 dump

  Organizing (from disk)
  vamtb -d d:\VAM sortvar  Reorganize your var directories with <creator>/*
              If a file already exists in that directory, CRC is checked before overwritting.
  vamtb -d d:\VAM statsvar will dump some statistics

  Database:
  vamtb -vvd d:\VAM dbs will scan your vars and create or if modification time is higher, update database

  Dependency graph (uses database)
  vamtb -vvd d:\VAM dotty will graph your collection one graph per var
  vamtb -vvd d:\VAM -f sapuzex.Cooking_Lesson.1 dotty will graph this var
  vamtb -vvd d:\VAM -f sapuzex.* dotty will graph vars matching

  Character encoding on windows:
  On windows cmd will use cp1252 so you might get some errors displaying international characters.
  Start vamtb with python -X utf8 vamtb.py <rest of parameters>

Options:
  -f TEXT                 Var file to act on.
  -d TEXT                 Use a specific VAM directory.
  -v, --verbose           Verbose (twice for debug).
  -x, --move / --no-move  When checking dependencies move vars with missing
                          dep in 00Dep.
  --help                  Show this message and exit.

Commands:
  checkdeps     Check dependencies of all var files.
  checkvars     Check all var files for consistency
  dbs           Scan vars and store props in db
  dotty         Gen dot graph of deps, one per var
  dump          Dump var meta.json
  noroot        Remove root node stored in pose presets
  printdep      Print dependencies of a var from reading meta.
  printrealdep  Print dependencies of a var from inspecting all json files.
  sortvar       Moves vars to subdirectory named by its creator
  statsvar      Get stats on all vars
```
## Tips
When using dbs subcommand, this will generate a sqlite file that you can browse you vars and included files insude with any tool compatible, like [sqlitebrowser](https://sqlitebrowser.org/).

For dotty subcommand to work, you will need dot from [graphiz](https://www.graphviz.org/download/) installed in c:\Graphviz\bin\dot.exe