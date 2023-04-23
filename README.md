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

  For specific command help use vamtb <command> --help

  For file pattern OPTION, you need to pass a regular expression like .*\.var
  (* can be replaced by %)

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
  anon           Upload var to Anonfiles.
  checkdep       Check dependencies of var recursively.
  checkvar       Check all var files for consistency.
  dbclean        Remove vars from DB which are not found on disk.
  dbdel          Remove one var from DB.
  dbscan         Scan vars and store props in db.
  dep            Depends of a var.
  dumpvar        Dump meta.json from var.
  dupinfo        Return duplication information.
  exists         Check wether vars exist in database.
  graph          Generate graph of deps, one per var.
  hub_resources  Get resources for creator.
  ia             Upload var to Internet Archive item.
  imageopt       Optimize images in vars.
  latest         Show "latest" version of var as an absolute filename.
  link           Link var in current directory to vam directory.
  multiup        Upload var to multiple place.
  nordep         Prints all var which don't have a reverse dependent.
  noroot         Remove root node stored in pose presets.
  orig           Revert to orig files.
  pluginpreset   Update Plugin presets to latest plugins found.
  printdep       Print dependencies of a var from reading meta.
  printrealdep   Print dependencies of a var from inspecting all json files.
  profile        Creates or selects a new VaM installation instance.
  rdep           Reverse depends of vars.
  renamevar      Rename file to var getting props from meta.json.
  repack         Packs anything to var.
  reref          Remove embedded content and point to reference var.
  setref         Set var and files as reference.
  sortvar        Moves vars to subdirectory named by its creator.
  statsvar       Get stats on all vars.
  varlink        Link var and dependent to current directory.
  zinfo          Return zip meta info of files in var.
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