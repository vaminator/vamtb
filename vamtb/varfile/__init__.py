'''Var file naming'''
import json
import time
import os
import re
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile, BadZipFile

import json
from vamtb import vamex
from vamtb.utils import *
from vamtb.file import FileName

class Var:

    def __init__(self, fileName, dir=None, zipcheck=False):

        # AddonDir if specified
        if dir:
            dir = Path(dir)
            if dir.name == "AddonPackages":
                self.__AddonDir = dir
            else:
                self.__AddonDir = Path(dir, "AddonPackages")

        # Full path pointing to existing file 
        self.__modified_time = 0
        self.__cksum = 0

        self.__Creator = ""
        self.__Resource = ""
        # Version as string 1, latest, min
        self.__sVersion = ""
        # integer version or 0
        self.__iVersion = 0

        # tempdir to extracted var
        self.__tmpDir = ""

        # Meta as dict
        self.meta = None

        # Associated Path .jpg
        self.__thumb = None

        # Verify and search var on disk
        self.__Path = self.__initvar(fileName)

        if zipcheck:
            self.extract()

        if self.__Path.with_suffix(".jpg").exists():
            self.__thumb = self.__Path.with_suffix(".jpg")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def __del__(self):
        debug(f"Erasing directory {self.__tmpDir}")
        if self.__tmpDir:
            self.__tmpTempDir.cleanup()
        pass

    def Creator(self):
        return self.__Creator

    def Path(self):
        return self.__Path

    def name(self):
        return ".".join([ self.Creator(), self.__Resource, str(self.__iVersion) if self.__iVersion else self.__sVersion ])

    def search(self, pattern)-> Path:
        fpath = self.__AddonDir
        debug(f"Searching for var...")
        if Path(fpath, self.Creator(), pattern).exists():
            debug(f"Found..")
            return [ Path(fpath, self.Creator(), pattern) ]
        debug(f"Listing files pattern **/{pattern} in {fpath}")
        pattern = re.sub(r'([\[\]])','[\\1]',pattern)
        return [ x for x in fpath.glob(f"**/{pattern}") if x.is_file() ]

    def __initvar(self, varname):
        f_varname = Path(varname)
        f_basename = f_varname.name

        try:
            self.__Creator, self.__Resource, self.__sVersion = f_basename.split('.',3)[0:3]
        except ValueError:
            error(f"Var {varname} has incorrect format")
            raise vamex.VarNameNotCorrect(varname)
        try:
            self.__iVersion = int(self.__sVersion)
        except ValueError:
            if self.__sVersion != "latest" and not self.__sVersion.startswith('min'):
                error(f"Var {varname} has incorrect extension {self.__sVersion}" )
                raise vamex.VarVersionNotCorrect(varname)
        try:
            _, _, _, ext = f_basename.split('.',4)
        except ValueError:
            ext = "var"

        if ext != "var":
            raise vamex.VarExtNotCorrect(varname)

        debug(f"Var {self.name()} is correct")
        # Search var on disk
        if Path(varname).exists() and Path(varname).is_file():
            return Path(varname)
        
        if varname.endswith(".var"):
            varname = varname[0:-4]

        if self.__iVersion:
            pattern = f"{varname}.var"
        else:
            pattern = f"{self.Creator()}.{self.__Resource}.*.var"
        vars = self.search(pattern = pattern)
        debug(f"Found {self.name()} in { '.'.join( [str(e) for e in vars ] )}")

        if not vars:
            raise vamex.VarNotFound(varname)

        # Extract .name prop
        vars = list(reversed(sorted(vars)))

        if len(vars) > 1:
            debug(f"Using {vars[0]} for {self.name()}")

        return vars[0]

    def __repr__(self) -> str:
        return f"{self.name()} [path : {self.__Path}]"

    def set_fprops(self):
        self.__modified_time = os.path.getmtime(self.__Path)
        self.__cksum = FileName(self.__Path).crc()

    def extract(self):
        self.__tmpTempDir = tempfile.TemporaryDirectory(prefix="vamtb_temp_")
        tmpPathdir = Path(self.__tmpTempDir.name)
        try:
            debug(f"Extracting zip {self.name()}...")
            ZipFile(self.__Path).extractall(tmpPathdir)
            debug(f"Done...")
        except Exception as e:
            self.__del__()
            raise
        else:
            self.__tmpDir = tmpPathdir
            debug(f"Extracted {self.name()} to {self.__tmpDir}")

    def unzip(func):
        """Decorate to extract zip"""
        def inner(self, *args, **kwargs):
            if not self.__tmpDir:
                self.extract()
            if self.__tmpDir:
                return func(self, *args, **kwargs)

        return inner

    @unzip
    def load_json_file(self, filename):
        res = FileName(Path(self.__tmpDir, filename)).json()
        if filename == "meta.json":
            self.meta = res
        return res

    @unzip
    def contains(self, pattern):
        """ Unzip var and returns list of crc of files matching name """
        matches = []
        for f in utils.search_files_indir(self.__tmpDir, pattern):
            debug(f"{f} matches contains('{pattern}')")
            matches.append(f"{FileName(f, calc_crc=True)}")
        return matches

    @unzip
    def open_file(self, fname):
        fn = FileName(Path(self.__tmpDir, fname))
        return fn.open()

    @unzip
    def dep_frommeta(self):
        self.meta = self.load_json_file("meta.json")
        if not( self.meta and "dependencies" in self.meta and self.meta['dependencies']):
            return []

        return self.meta['dependencies']
    
    @unzip
    def files(self, path=None, with_meta = False):
        if not path:
            path = self.__tmpDir
        for entry in os.scandir(path):
            if entry.is_dir(follow_symlinks=False):
                yield from self.files(entry.path)
            if entry.is_file():
                if with_meta or entry.name != "meta.json":
                    yield FileName(entry, calc_crc=False)

    @unzip
    def dep_from_files(self, full=False):
        """
        Full=True will also return files referenced from the dependent var"""
        all_deps = []
        for file in self.files():
            try:
                deps = file.jsonDeps()
            except Exception as e:
                continue
            if not full:
                varnames = list(set([ v.split(':')[0] for v in deps['var'] ]))
                if varnames:
                    debug(f"File {self.name()} references vars: {','.join(sorted(varnames))}")
                all_deps.extend(varnames)
            else:
                all_deps.extend(deps['var'])
        all_deps = list(set(all_deps))
        return all_deps

    depend_node = []
    @unzip
    def depend(self, recurse = False, init = True, check = True):
        global depend_node

        # For dependency loop tracking, init nodes
        if init:
            depend_node = [ self.name() ]
        for dep in self.dep_from_files():
            if dep not in depend_node:
                depend_node.append(dep)
                try:
                    with  Var(dep, self.__AddonDir) as var:
                        info(f"{self.name()} depends on {var}")
                        if recurse:
                            var.depend(recurse=True, init = False, check = check)
                except vamex.VarNotFound as e:
                    if check:
                        error(f"{dep} Not found")
            else:
                info(f"Detected loop from {self.name()} with {dep}")
        return depend_node

    @unzip
    def remroot(self):

        debug(f"Removing root from {self.name()}")
        tmpfd, tmpname = tempfile.mkstemp(dir=self.__AddonDir)
        os.close(tmpfd)

        with ZipFile(tmpname, 'w') as zout:
            zout.comment = b""
            for file in self.files(with_meta=True):
                rel_file = str(file.path().relative_to(self.__tmpDir).as_posix())
                if rel_file.endswith(".vap") and rel_file.startswith("Custom/Atom/Person/Pose/"):
                    jvap = file.json()
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
        shutil.move( tmpname, f"{self.name()}.var" )

    def move_creator(self):


        files_to_move = [ self.__Path ]
        if self.__thumb:
            files_to_move.append(self.__thumb)

        for file_to_move in files_to_move:
            newpath = Path(self.__AddonDir, self.Creator(), 
                        f"{file_to_move.name}")

            if str(file_to_move).lower() == str(newpath).lower():
                debug(f"Not moving {self.__Path}")
                return
            try:
                os.makedirs(newpath.parent)
            except FileExistsError:
                pass

            if not newpath.is_file():
                info(f"Moved {file_to_move} to directory {newpath.parent}")
                shutil.move(file_to_move, newpath)
                continue

            fcrc = FileName(file_to_move, calc_crc=True).crc()
            ncrc = FileName(newpath, calc_crc=True).crc()

            if fcrc == ncrc:
                info("Exact same file exists, removing duplicate")
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
            listOfFileNames = [f for f in myvar.namelist() if re.search(pattern, f) is not None]
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


def prep_tree(file, dir, creator, do_move = False):

    # Get type
    mtype = get_type(file)
    debug(f"Detected file {file} as type {mtype}")

    if mtype == utils.T_DIR:
        # Copy subtree relative to a root (asked to user)
        parents = [ Path(file) ] 
        for p in Path(file).parents:
            parents.append(p)
        for i, p in enumerate(parents, start=1):
            tab='\t'
            print(f"{i}{tab}{p}")
        root = int(input("Select relative root dir:")) - 1
        reldir = parents[root]
        # FIXME this copies all directories at the same level, not only the selected one
        shutil.copytree(reldir, dir, dirs_exist_ok = True)
        if do_move:
            shutil.rmtree(file)
            
        return

    # Require some files
    reqfiles = get_reqfile(file, mtype)
    nl = '\n'
    debug(f"List of files:{nl}{nl.join(list(map(lambda x:x.as_posix(), reqfiles)))}")

    # Create dirstruct
    d = None
    if mtype == utils.T_SCENE:
        d = Path(dir,"Saves", "scene")

    if mtype == utils.T_ASSET:
        d = Path(dir,"Custom", "Assets", creator)

    if mtype & utils.T_CLOTH:
        if mtype & utils.T_FEMALE:
            gend = "Female"
        elif mtype & utils.T_MALE:
            gend = "Male"
        else:
            assert(False)
        d = Path(dir,"Custom", "Clothing", gend, creator)

    if not d:
        listdirs = []
        for p in Path(dir).glob("**/*"):
            if p.is_dir():
                listdirs.append(Path(os.path.relpath(p, dir)))

        for i, ldir in enumerate(listdirs, start=1):
            tab='\t'
            print(f"{i}{tab}{ldir}")
        cd = input("Choose directory to copy that to (or type new dir relative to var root):") 
        try:
            idx = int(i)-1
            d = list(listdirs)[idx]
        except ValueError:
            d = Path(dir, cd).resolve()
        finally:
            d = Path(dir, d)

    debug(f"Puting file in {d.resolve()}")
    d.mkdir(parents=True, exist_ok=True)

    # Copy or Move files
    for f in reqfiles:
        if do_move:
            shutil.move(f"{f}", f"{d}")
        else:
            shutil.copy(f, d)

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
