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

  Dependency handling (from disk or database)
  vamtb checkdeps
  vamtb -f sapuzex.Cooking_Lesson.1 checkdeps
  vamtb -f -b sapuzex.Cooking_Lesson.1 checkdep
  vamtb -f ClubJulze.Bangkok.1 printdep
  vamtb -f ClubJulze.Bangkok.1 printrealdep

  Meta json handling (from disk)
  vamtb -f sapuzex.Cooking_Lesson.1 dump

  Organizing (from disk)
  vamtb sortvar  Reorganize your var directories with <creator>/*
              If a file already exists in that directory, CRC is checked before overwritting.
  vamtb statsvar will dump some statistics

  Database:
  vamtb dbs will scan your vars and create or if modification time is higher, update database

  Dependency graph (uses database)
  vamtb dotty will graph your collection one graph per var
  vamtb -f sapuzex.Cooking_Lesson.1 dotty will graph this var
  vamtb -f sapuzex.* dotty will graph vars matching

  Duplication (uses database)
  vamtb -f sapuzex.Cooking_Lesson.1 dupinfo will print duplication info
  vamtb -f Wolverine333.% reref will dedup files from creator
  vamtb -x colorcorrect.assetbundle reref will remove all embedded colorcorrect.assetbundle from every var BUT the reference var

  Character encoding on windows:
  On windows cmd will use cp1252 so you might get some errors displaying international characters.
  Start vamtb with python -X utf8 vamtb.py <rest of parameters>

  File filters:
  You can use wildcards with % caracter: vamtb -f Community.% dupinfo

  You can get help for a command with
  vamtb reref --help

Options:
  -f TEXT                         Var file to act on.
  -d TEXT                         Use a specific VAM directory.
  -x TEXT                         Only dedup this file.
  -v, --verbose                   Verbose (twice for debug).
  -p, --progress / --no-progress  Add progress bar.
  -m, --move / --no-move          When checking dependencies move vars with
                                  missing dep in 00Dep.
  -r, --ref / --no-ref            Only select non reference vars for dupinfo.
  -b, --usedb / --no-usedb        Use DB.
  --help                          Show this message and exit.

Commands:
  checkdeps     Check dependencies of all var files.
  checkvars     Check all var files for consistency.
  dbs           Scan vars and store props in db.
  dump          Dump meta.json from var.
  dupinfo       Return duplication information.
  graph         Generate graph of deps, one per var.
  noroot        Remove root node stored in pose presets.
  printdep      Print dependencies of a var from reading meta.
  printrealdep  Print dependencies of a var from inspecting all json files.
  reref         Remove embedded content and point to reference var.
  sortvar       Moves vars to subdirectory named by its creator.
  statsvar      Get stats on all vars.
```
## Tips
When using dbs subcommand, this will generate a sqlite file that you can browse you vars and included files with any compatible tool. I suggest [sqlitebrowser](https://sqlitebrowser.org/).


For graph subcommand to work, you will need dot from [graphviz](https://www.graphviz.org/download/) installed in c:\Graphviz\bin\dot.exe