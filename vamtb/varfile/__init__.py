'''Var file naming'''
import json
import time
import os
import re
import shutil
import tempfile
import json
from pathlib import Path
from zipfile import ZipFile, BadZipFile

from vamtb.file import FileName
from vamtb.vamex import *
from vamtb.utils import *
from vamtb.log import *

class VarFile:

    def __init__(self, inputName) -> None:
        inputName or critical("Tried to create a var but gave no filename", doexit=True)
        self.__Creator = ""
        self.__Resource = ""
        # Version as string 1, latest, min
        self.__sVersion = ""
        # integer version or 0
        self.__iVersion = 0
        # Min version or 0
        self.__iMinVer = 0

        if not isinstance(inputName, Path):
            inputName = Path(inputName)

        f_basename = inputName.name
        try:
            self.__Creator, self.__Resource, self.__sVersion = f_basename.split('.',3)[0:3]
        except ValueError:
            error(f"Var {inputName} has incorrect format")
            raise VarNameNotCorrect(inputName)
        try:
            self.__iVersion = int(self.__sVersion)
        except ValueError:
            if self.__sVersion == "latest":
                pass
            elif self.__sVersion.startswith('min'):
                try:
                    self.__iMinVer = int(self.__sVersion[3:])
                except ValueError:
                    raise VarExtNotCorrect(inputName)
            else:
                error(f"Var {inputName} has incorrect extension {self.__sVersion}" )
                raise VarExtNotCorrect(inputName)
        try:
            _, _, _, ext = f_basename.split('.',4)
        except ValueError:
            pass
        else:
            if ext != "var":
                raise VarExtNotCorrect(inputName)
        debug(f"Var {inputName} is compliant")

    @property
    def var(self) -> str:
        return f"{self.__Creator}.{self.__Resource}.{self.__sVersion}"

    @property
    def var_nov(self) -> str:
        return f"{self.__Creator}.{self.__Resource}"

    @property
    def file(self) -> str:
        return self.var + ".var"

    @property
    def creator(self) -> str:
        return self.__Creator

    @property
    def resource(self) -> str:
        return self.__Resource

    @property
    def version(self) -> str:
        return self.__sVersion

    @property
    def iversion(self) -> int:
        return self.__iVersion

    @property
    def minversion(self) -> int:
        return self.__iMinVer

class Var(VarFile):

    def __init__(self, multiFileName, dir=None, zipcheck=False):
        """
        multiFileName can be a.b.c, a.b.c.var, c:/tmp/a.b.c or c:/tmp/a.b.c.var
        in the two first cases, dir is required to find the var on disk
        zipcheck will extract the zip to a temporary directory
        """
        # tempdir to extracted var
        multiFileName or critical("Tried to create a var but gave no filename", doexit=True)
        self.__tmpDir = None
        VarFile.__init__(self, multiFileName)

        # AddonDir if specified
        if dir:
            dir = Path(dir)
            if dir.name == "AddonPackages":
                self.__AddonDir = dir
            else:
                self.__AddonDir = dir / "AddonPackages"
        else:
            self.__AddonDir = None

        # Meta as dict
        self._meta = None

        # Associated Path .jpg
        self.__thumb = None

        # Verify and resolve var on disk
        self._path = Path(self.__resolvevar(multiFileName))

        if zipcheck:
            self.extract()

        if self._path.with_suffix(".jpg").exists():
            self.__thumb = self.path.with_suffix(".jpg")

        debug(f"Var {multiFileName} is found as {self._path}")

    @property
    def path(self) -> str:
        return self._path

    @property
    def evar(self) -> str:
        """ var from pathname (latest and min resolved) """
        return f"{Path(self.path).with_suffix('').name}"

    @property
    def crc(self):
        return FileName(self.path).crc

    @property
    def mtime(self):
        return FileName(self.path).mtime

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def __del__(self):
        if self.__tmpDir:
            debug(f"Erasing directory {self.__tmpDir}")
            self.__tmpTempDir.cleanup()
        pass

    def search(self, pattern)-> Path:
        fpath = self.__AddonDir
        debug(f"Listing files pattern **/{pattern} in {fpath}")
        pattern = re.sub(r'([\[\]])','[\\1]',pattern)
        return [ x for x in fpath.glob(f"**/{pattern}") if x.is_file() ]

    def __resolvevar(self, multiname):
        """This will return the real var as an existing Path"""
        if Path(multiname).exists() and Path(multiname).is_file():
            return Path(multiname)

        # Not a full path var, search var on disk
        if self.iversion :
            pattern = self.file
        elif self.version == "latest" or self.minversion:
            pattern = self.creator + "." + self.resource + ".*.var"
        else:
            assert(False)

        vars = self.search(pattern = pattern)
        if not vars:
            raise VarNotFound(self.var)

        if self.version == "latest":
            rsortedvars = list(reversed(sorted(vars, key=lambda x: int(x.name.split('.')[2]))))
            return rsortedvars[0]
        elif self.minversion :
            vars = [ e for e in vars if int(e.name.split('.')[2]) >= self.minversion ]
            sortedvars = list(sorted(vars, key=lambda x: int(x.name.split('.')[2])))
            if not sortedvars:
                raise VarNotFound(self.var)
            return sortedvars[0]
        else:
            assert(len(vars) == 1)
            return vars[0]

    def __repr__(self) -> str:
        return f"{self.var} [path : {self.path}]"

    def extract(self):
        self.__tmpTempDir = tempfile.TemporaryDirectory(prefix="vamtb_temp_")
        tmpPathdir = Path(self.__tmpTempDir.name)
        try:
            debug(f"Extracting zip {self.var}...")
            with ZipFile(self.path) as z:
                z.extractall(tmpPathdir)
            debug(f"Extracting done...")
        except Exception as e:
#            self.__del__()
            raise
        else:
            self.__tmpDir = tmpPathdir
            debug(f"Extracted {self.var} to {self.__tmpDir}")

    def meta(self) -> dict:
        if not self._meta:
            self._meta = self.load_json_file("meta.json")
        return self._meta

    @property
    def tmpDir(self):
        return self.__tmpDir

    def unzip(func):
        """Decorator to extract zip"""
        def inner(self, *args, **kwargs):
            if not self.__tmpDir:
                self.extract()
            if self.__tmpDir:
                return func(self, *args, **kwargs)

        return inner

    @unzip
    def load_json_file(self, filename) -> dict:
        return FileName(Path(self.__tmpDir, filename)).json

    @unzip
    def open_file(self, fname):
        fn = FileName(Path(self.__tmpDir, fname))
        return fn.open()

    @unzip
    def dep_frommeta(self):
        if not( self.meta() and "dependencies" in self.meta() and self.meta()['dependencies']):
            return []

        return self.meta()['dependencies']
    
    @unzip
    def dep_fromfiles(self, with_file = False):
        all_deps = []
        for file in self.files():
            try:
                deps = file.jsonDeps
            except (UnicodeDecodeError, json.decoder.JSONDecodeError):
                continue

            if with_file:
                elements = deps['var']
            else:
                elements = list(set([ v.split(':')[0] for v in deps['var'] ]))
            if elements:
                debug(f"File {self.var} references vars: {','.join(sorted(elements))}")
                all_deps.extend(elements)
        if with_file:
            all_deps = [ e for e in list(set(all_deps)) if e.split(':')[0] != self.var ]
        else:
            all_deps = [ e for e in list(set(all_deps)) if e != self.var ]
        return all_deps

    depend_node = []

    @unzip
    def depend(self, recurse = False, init = True, check = True):
        global depend_node

        # For dependency loop tracking, init nodes
        if init:
            depend_node = [ self.var ]
        for dep in self.dep_fromfiles():
            if dep not in depend_node:
                depend_node.append(dep)
                try:
                    with  Var(dep, self.__AddonDir) as var:
                        debug(f"{self.var} depends on {var}")
                        if recurse:
                            var.depend(recurse=True, init = False, check = check)
                except VarNotFound as e:
                    if check:
                        error(f"{dep} Not found")
                    raise
            else:
                debug(f"Avoiding loop from {self.var} with {dep}")
        return depend_node

    def ziprel(self, fname):
        return Path(os.path.relpath(fname, self.__tmpDir)).as_posix()

    @unzip
    def files(self, with_meta=False, path=None):
        if not path:
            path = self.__tmpDir
        for entry in os.scandir(path):
            if entry.is_dir(follow_symlinks=False):
                yield from self.files(with_meta=with_meta, path=entry.path)
            if entry.is_file():
                if with_meta or entry.name != "meta.json":
                    yield FileName(entry, calc_crc=False)

    @unzip
    def remroot(self):
        debug(f"Removing root from {self.var}")
        tmpfd, tmpname = tempfile.mkstemp(dir=self.__AddonDir)
        os.close(tmpfd)

        with ZipFile(tmpname, 'w') as zout:
            zout.comment = b""
            for file in self.files(with_meta=True):
                rel_file = str(file.path.relative_to(self.__tmpDir).as_posix())
                if rel_file.endswith(".vap") and rel_file.startswith("Custom/Atom/Person/Pose/"):
                    jvap = file.json
                    jvap_storables = jvap['storables']
                    jvap_storables_noroot = []

                    for s in jvap_storables:
                        if s['id'] not in ['control', 'CharacterPoseSnapRestore']:
                            jvap_storables_noroot.append(s)
                        else:
                            pass
                            info(f"Removing root from var {rel_file}")
                    jvap['storables'] = jvap_storables_noroot

                    zout.writestr(rel_file, json.dumps(jvap, indent=4))
                else:
                    zout.writestr(rel_file, file.read())
        shutil.move( tmpname, self.file )

    def move_creator(self):
        files_to_move = [ self.path ]
        if self.__thumb:
            files_to_move.append(self.__thumb)

        for file_to_move in files_to_move:
            newpath = Path(self.__AddonDir, self.creator,
                        f"{file_to_move.name}")

            if str(file_to_move).lower() == str(newpath).lower():
                debug(f"Not moving {self.path}")
                return
            try:
                os.makedirs(newpath.parent)
            except FileExistsError:
                pass

            if not newpath.is_file():
                info(f"Moved {file_to_move} to directory {newpath.parent}")
                shutil.move(file_to_move, newpath)
                continue

            fcrc = FileName(file_to_move, calc_crc=True).crc
            ncrc = FileName(newpath, calc_crc=True).crc

            if fcrc == ncrc:
                info(f"Exact same file exists, removing duplicate {self.path}")
                try:
                    Path.unlink(file_to_move)
                except PermissionError:
                    error(f"Couldnt remove {file_to_move}")
            else:
                error(f"File {file_to_move} and {newpath} have same name but crc differ {fcrc} , {ncrc}. Remove yourself.") 

def pattern_var(fname, pattern):
    """ List files within var matching a pattern """
    info(f"Searching thumb for {fname}")
    try:
        with ZipFile(fname, mode='r') as myvar:
            listOfFileNames = [ f for f in myvar.namelist() if re.search(pattern, f) is not None ]
            return listOfFileNames
    except BadZipFile as e:
        error(f"{fname} is not a correct zipfile ({e})")


def mcopytree(src, dst):
    def ignore(path, content_list):
        return [
            content
            for content in content_list
            if os.path.isdir(os.path.join(path, content))
        ]    
    shutil.copytree(f"{src}", f"{dst}", ignore=ignore, dirs_exist_ok=True)


def search_and_replace_dir(mdir, text, subst, enc):
    text=Path(text.removeprefix("SELF:/")).name
    text = re.escape(text)
    pattern = fr'"[^"]*{text}"'
    _replace_re = re.compile(pattern)
    for dirpath, dirnames, filenames in os.walk(mdir):
        for file in filenames:
            if Path(file).suffix in (".vab", ".vmb", ".dll", ".jpg", ".png", "tif", ".ogg", ".wav", ".mp3", ".AssetBundle", ".assetbundle"):
                continue
            if Path(file).name == "meta.json":
                continue
            file = os.path.join(dirpath, file)
            tempfile = file + ".temp"
            with open(tempfile, "w", encoding="utf-8") as target:
                # debug(f"Rewriting {file}")
                with open(file, "r", encoding=enc) as source:
                    try:
                        for line in source:
                            if _replace_re.findall(line):
                                info(f"Found a match in file {file}")
                            line = _replace_re.sub(f'"{subst}"', line)
                            target.write(line)
                    except UnicodeDecodeError:
                        error(f"Could not decode file {file} with encoding {enc}")
                        timeout = 0.001
                        time.sleep(timeout)
                        while(timeout < 2):
                            try:
                                os.remove(tempfile)
                            except PermissionError:
                                timeout *= 2
                            except FileNotFoundError:
                                raise UnicodeDecodeError
            os.remove(file)
            os.rename(tempfile, file)