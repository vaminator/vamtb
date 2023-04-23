# VamTB

-- VamToolBox --

## Install
Build from source and install dependencies:
````
python setup.py install
````

Or use a prebuilt binary release (see Releases)

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
  -d TEXT                         Use a specific VAM directory.
  -f TEXT                         Var file to act on.
  -p, --progress / --no-progress  Add progress bar.
  -v, --verbose                   Verbose (twice for debug).
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