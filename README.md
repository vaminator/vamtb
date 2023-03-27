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
The batch file calls :
````
python -X utf8 vamtb.py ...
````

At any time, to interrupt, hit twice ctrl-c.

## Options
```text
Usage: vamtb.py [OPTIONS] COMMAND [ARGS]...

  VAM Toolbox For full help and all commands use vamtb --help

  Dependency handling (from disk or database):
  vamtb checkdeps
  vamtb -f sapuzex.Cooking_Lesson.1 checkdeps
  vamtb -f -b sapuzex.Cooking_Lesson.1 checkdep
  vamtb -f ClubJulze.Bangkok.1 printdep
  vamtb -f ClubJulze.Bangkok.1 printrealdep

  Meta json handling (from disk):
  vamtb -f sapuzex.Cooking_Lesson.1 dump

  Organizing (from disk):
  vamtb sortvar  Reorganize your var directories with <creator>/*
              If a file already exists in that directory, CRC is checked before overwritting.
  vamtb statsvar will dump some statistics

  Database:
  vamtb dbsscan will scan your vars and create or if modification time is higher, update database
  vamtb -f sapuzex.Cooking_Lesson.1 dbdel will remove any reference to var and files in the DB

  Dependency graph (uses database):
  vamtb graph will graph your collection one graph per var
  vamtb -f sapuzex.Cooking_Lesson.1 graph will graph this var
  vamtb -f sapuzex.* graph will graph vars matching

  Deduplication (uses database):
  vamtb -f sapuzex.Cooking_Lesson.1 dupinfo will print duplication info
  vamtb -f Wolverine333.% reref will dedup files from creator
  vamtb -x colorcorrect.assetbundle reref will remove all embedded colorcorrect.assetbundle from every var BUT the reference var

  Upload (uses database):
  vamtb -f sapuzex.Cooking_Lesson.1 ia will upload each var to an Internet Archive item
  vamtb -f sapuzex.Cooking_Lesson.1 anon will upload each var to anonfiles (need an account for the API key)

  File filters:
  You can use wildcards with % caracter: vamtb -f Community.% dupinfo

  You can get help for a command with
  vamtb <command> --help

Options:
  -a, --force / --no-force        Do not ask for confirmation.
  -b, --usedb / --no-usedb        Use DB.
  -c, --cc / --no-cc              Only upload CC license content
  -d TEXT                         Use a specific VAM directory.
  -e, --meta / --no-meta          Only reset subject metadata.
  -f TEXT                         Var file to act on.
  -g TEXT                         Input directory for var creation.
  -i TEXT                         Internet Archive identifier prefix (defaults
                                  to vam1__).
  -j, --optimize                  Image Optimize level (none:No png to jpg
                                  that is lossless, 1: Jpeg qual 90%, 2: Jpeg
                                  qual 75%).
  -m, --move / --no-move          When checking dependencies move vars with
                                  missing dep in 00Dep.
  -n, --dryrun / --no-dryrun      Dry run on what would be uploaded.
  -p, --progress / --no-progress  Add progress bar.
  -q, --remove / --no-remove      Remove var from DB.
  -r, --ref / --no-ref            Only select non reference vars for dupinfo.
  -s, --full / --no-full          For scenes, upload not only scene jpg but
                                  all jpg to IA.
  -v, --verbose                   Verbose (twice for debug).
  -x TEXT                         Only dedup this file.
  -z, --setref / --no-setref      Set var as reference.
  --help                          Show this message and exit.

Commands:
  anon          Upload var to Anonfiles.
  checkdep      Check dependencies of var recursively.
  checkvar      Check all var files for consistency.
  dbclean       Remove vars from DB which are not found on disk.
  dbdel         Remove one var from DB.
  dbscan        Scan vars and store props in db.
  dumpvar       Dump meta.json from var.
  dupinfo       Return duplication information.
  graph         Generate graph of deps, one per var.
  gui           There's no graphical user interface
  ia            Upload var to Internet Archive item.
  imageopt      Optimize images in vars.
  link          Link var and dependent to configured directory.
  multiup       Upload var to multiple place.
  noroot        Remove root node stored in pose presets.
  orig          Revert to orig files.
  printdep      Print dependencies of a var from reading meta.
  printrealdep  Print dependencies of a var from inspecting all json files.
  reref         Remove embedded content and point to reference var.
  setref        Set var and files as reference.
  sortvar       Moves vars to subdirectory named by its creator.
  statsvar      Get stats on all vars.
  zinfo         Return zip meta info of files in var.
```
## Database
The dbscan subcommand will generate a sqlite file that you can browse. You will find tables for your vars and files and you can access that with any compatible tool like [sqlitebrowser](https://sqlitebrowser.org/).

## Graphs
For graph subcommand to work, you will need dot from [graphviz](https://www.graphviz.org/download/) installed in c:\Graphviz\bin\dot.exe

## Internet archive
Your IA credentials should be configured before using ia to upload to archive.org

```text
ia configure
```