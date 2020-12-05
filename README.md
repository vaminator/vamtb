# vamtb
Vam toolbox

Usage: vamtb.py [OPTIONS] COMMAND [ARGS]...

  VAM Toolbox

  Examples:

  vamtb -d d:\VAM -vv -f sapuzex.Cooking_Lesson.1 checkdep
  vamtb -d d:\VAM -f ClubJulze.Bangkok.1 printdep
  vamtb -d d:\VAM -f sapuzex.Cooking_Lesson.1 dump
  vamtb -d d:\VAM -f sapuzex.Cooking_Lesson.1 printdep
  vamtb -d d:\VAM -f ClubJulze.Bangkok.1.var thumb
  vamtb -d d:\VAM -v checkdeps
  vamtb -d d:\VAM sortvar  (caution this will reorganize your var directories)
  vamtb -d d:\VAM statsvar
  vamtb -d d:\VAM thumb

Options:
  -d TEXT        VAM directory.
  -c TEXT        VAM custom directory.
  -f TEXT        Var file.
  -v, --verbose  Verbose (twice for debug).
  --help         Show this message and exit.

Commands:
  autoload   Check vars having autoloading of morph
  checkdep   Check dependencies of a var
  checkdeps  Check dependencies of all var files
  convert    Convert tree to var
  dump       Dump var meta.json
  printdep   Print dependencies of a var
  sortvar    Moves vars to subdirectory named by its creator
  statsvar   Get stats on all vars
  thumb      Gen thumbs from var file(s)
