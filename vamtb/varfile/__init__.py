'''Var file naming'''
import json
import os
import re
import shutil
import tempfile
import json
from pprint import pp
from pathlib import Path
from zipfile import ZipFile

from vamtb.db import Dbs
from vamtb.file import FileName

from vamtb.vamex import *
from vamtb.utils import *
from vamtb.log import *

class VarFile:

    def __init__(self, inputName, use_db = False) -> None:
        inputName or critical("Tried to create a var but gave no filename", doexit=True)
        self.__Creator = ""
        self.__Resource = ""
        # Version as string 1, latest, min
        self.__sVersion = ""
        # integer version or 0
        self.__iVersion = 0
        # Min version or 0
        self.__iMinVer = 0
        # Db if a reference was provided
        self.__Dbs = Dbs if use_db else None

        if not isinstance(inputName, Path):
            inputName = Path(inputName)

        f_basename = inputName.name
        try:
            self.__Creator, self.__Resource, self.__sVersion = f_basename.split('.',3)[0:3]
        except ValueError:
            error(f"Var has incorrect format: {inputName}")
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
                error(f"Var has incorrect version: {inputName} version: {self.__sVersion}" )
                raise VarExtNotCorrect(inputName)
        try:
            _, _, _, ext = f_basename.split('.',4)
        except ValueError:
            pass
        else:
            if ext != "var":
                error(f"Var has incorrect extension: {inputName}" )
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

    def db_exec(self, sql, row):
        if self.__Dbs:
            self.__Dbs.execute(sql, row)
        else:
            assert(False)

    def db_fetch(self, sql, row):
        if self.__Dbs:
            return self.__Dbs.fetchall(sql, row)
        else:
            assert(False)

    def db_commit(self, rollback = False):
        if self.__Dbs:
            if rollback:
                self.__Dbs.getConn().rollback()
            else:
                self.__Dbs.getConn().commit()
        else:
            assert(False)

    def store_var(self):
        """ Insert (if NE) or update (if Time>) or do nothing (if Time=) """
        creator, version, modified_time, cksum = (self.creator, self.version, self.mtime, self.crc)
        size = FileName(self.path).size
        v_isref="YES" if creator in C_REF_CREATORS else "UNKNOWN"

        meta = self.meta()
        license = meta['licenseType']

        sql = """INSERT INTO VARS(VARNAME,ISREF,CREATOR,VERSION,LICENSE,MODIFICATION_TIME,SIZE,CKSUM) VALUES (?,?,?,?,?,?,?,?)"""
        row = (self.var, v_isref, creator, version, license, modified_time, size, cksum)
        self.db_exec(sql, row)

        for f in self.files(with_meta=True):
            crcf = f.crc
            sizef = f.size
            f_isref = "YES" if creator in C_REF_CREATORS else "UNKNOWN"

            sql = """INSERT INTO FILES (ID,FILENAME,ISREF,VARNAME,SIZE,CKSUM) VALUES (?,?,?,?,?,?)"""
            row = (None, self.ziprel(f.path), f_isref, self.var, sizef, crcf)
            self.db_exec(sql, row)

        debug(f"Stored var {self.var} and files in databases")
        sql = """INSERT INTO DEPS(ID,VAR,DEPVAR,DEPFILE) VALUES (?,?,?,?)"""
        for dep in self.dep_fromfiles(with_file=True):
            depvar, depfile = dep.split(':')
            depfile = depfile.lstrip('/')
            row = (None, self.var, depvar, depfile)
            self.db_exec(sql, row)

        self.db_commit()
        return True

    def store_update(self, confirm = True):
        if self.exists():
            info(f"{self.var} already in database")
            if FileName(self.path).mtime == self.get_modtime or FileName(self.path).crc == self.get_cksum:
                return False
            info(f"Database is not inline.")
            if confirm == False:
                res = "Y"
            else:
                res = input(f"Remove older DB for {self.path} ?[Y]N")
            if not res or res == "Y":
                self.db_delete() 
                self.db_commit()
            else:
                self.db_commit(rollback = True)
                return False
        return self.store_var()

    def exists(self):
        if self.var.endswith(".latest"):
            return (self.latest() != None)
        elif self.version.startswith("min"):
            return (self.min() != None)
        else:
            return (self.get_prop_vars("VARNAME") != None)

    def latest(self):
        assert(self.var.endswith(".latest"))
        sql="SELECT VARNAME FROM VARS WHERE VARNAME LIKE ? COLLATE NOCASE"
        var_nov = self.var_nov
        row = (f"{var_nov}%", )
        res = self.db_fetch(sql, row)
        versions = [ e[0].split('.',3)[2] for e in res ]
        versions.sort(key=int, reverse=True)
        if versions:
            return f"{var_nov}.{versions[0]}"
        else:
            return None

    def min(self):
        assert(self.version.startswith("min"))
        minver = self.minversion
        sql="SELECT VARNAME FROM VARS WHERE VARNAME LIKE ? COLLATE NOCASE"
        var_nov = self.var_nov
        row = (f"{var_nov}%", )
        res = self.db_fetch(sql, row)
        versions = [ e[0].split('.',3)[2] for e in res ]
        versions = [ int(v) for v in versions if int(v) >= minver ]
        versions.sort(key=int, reverse=True)
        if versions:
            return f"{var_nov}.{versions[0]}"
        else:
            return None

    def get_prop_vars(self, prop_name):

        sql = f"SELECT {prop_name} FROM VARS WHERE VARNAME=?"
        row = (self.var,)
        res = self.db_fetch(sql, row)
        if res:
            return res[0][0]
        else:
            return None

    def get_prop_files(self, filename:str, prop_name:str):
        sql = f"SELECT {prop_name} FROM FILES WHERE FILENAME=? AND VARNAME=?"
        row = (filename, self.var)
        res = self.db_fetch(sql, row)
        if res:
            return res[0][0]
        else:
            return None

    def get_dep(self):
        sql = f"SELECT DISTINCT DEPVAR FROM DEPS WHERE VAR=?"
        row = (self.var,)
        res = self.db_fetch(sql, row)
        res = [ e[0] for e in res ]
        return res if res else []

    def rec_dep(self, stop = True):
        def rec(var:Var, depth=0):
            msg = " " * depth + f"Checking dep of {var.var}"
            if not var.exists():
                warn(f"{msg:<130}" + ": Not Found")
                if stop:
                    raise VarNotFound(var.var)
            else:
                info(f"{msg:<130}" + ":     Found")
            sql = f"SELECT DISTINCT DEPVAR FROM DEPS WHERE VAR=?"
            row = (var.var,)
            res = self.db_fetch(sql, row)
            res = [ e[0] for e in res ]
            for varfile in res:
                try:
                    depvar = VarFile(varfile, use_db=True)
                except (VarExtNotCorrect, VarNameNotCorrect, VarVersionNotCorrect):
                    error(f"We skipped a broken dependency from {self.var}")
                    continue
                rec(depvar, depth+1 )
        rec(self)

    def db_files(self, with_meta = True):
        sql = f"SELECT FILENAME FROM FILES WHERE VARNAME=?"
        if not with_meta:
            sql = sql + " AND FILENAME NOT LIKE '%meta.json'"
        row = (self.var,)
        res = self.db_fetch(sql, row)
        if res:
            return [ e[0] for e in res ]
        else:
            return []

    def db_delete(self):
        row = (self.var,)
        sql = f"DELETE FROM VARS WHERE VARNAME=?"
        self.db_exec(sql, row)
        sql = f"DELETE FROM FILES WHERE VARNAME=?"
        self.db_exec(sql, row)
        sql = f"DELETE FROM DEPS WHERE VAR=?"
        self.db_exec(sql, row)

    def get_file_cksum(self, filename):
        return self.get_prop_files(filename, "CKSUM")

    def get_file_size(self, filename):
        return self.get_prop_files(filename, "SIZE")

    def get_numfiles(self, with_meta = False):
        sql = f"SELECT COUNT(*) FROM FILES WHERE VARNAME == ?"
        if not with_meta:
            sql = sql + " AND FILENAME != 'meta.json'"
        row = (self.var, )
        return self.db_fetch(sql, row)[0][0]

    def get_refvar_forfile(self, file):
        cksum = self.get_file_cksum(file)
        sql = f"SELECT VARNAME, FILENAME FROM FILES WHERE CKSUM=? AND ISREF='YES' AND VARNAME!=? AND FILENAME LIKE ? GROUP BY VARNAME"
        row = (cksum, self.var, f"%{Path(file).name}")
        res = self.db_fetch(sql, row)
        if res:
            return res
        else:
            return None

    @property
    def license(self):
        return self.get_prop_vars("LICENSE")

    @property
    def size(self):
        return self.get_prop_vars("SIZE")

    @property
    def get_ref(self):
        return self.get_prop_vars("ISREF")

    @property
    def get_modtime(self):
        return self.get_prop_vars("MODIFICATION_TIME")

    @property
    def get_cksum(self):
        return self.get_prop_vars("CKSUM")

class Var(VarFile):

    def __init__(self, multiFileName, dir=None, use_db = False, zipcheck=False):
        """
        multiFileName can be a.b.c, a.b.c.var, c:/tmp/a.b.c or c:/tmp/a.b.c.var
        in the two first cases, dir is required to find the var on disk
        zipcheck will extract the zip to a temporary directory
        """
        # tempdir to extracted var
        multiFileName or critical("Tried to create a var but gave no filename", doexit=True)
    
        self.__tmpDir = None
        VarFile.__init__(self, multiFileName, use_db)

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

    @property
    def addondir(self):
        return self.__AddonDir

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
        assert(fpath)
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
                debug(f"File {file} in {self.var} references vars: {','.join(sorted(elements))}")
                all_deps.extend(elements)
        if with_file:
            all_deps = [ e for e in list(set(all_deps)) if e.split(':')[0] != self.var ]
        else:
            all_deps = [ e for e in list(set(all_deps)) if e != self.var ]
        return all_deps

    depend_node = []

    @unzip
    def depend(self, recurse = False, init = True, check = True, stop = True):
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
                    if stop:
                        raise
                else:
                    if check:
                        info(f"{dep} Found")
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

    def treedown(self):
        """
        Return down dependency graph
        Depth first
        """
        td_vars = {}
        def rec(var:Var):
            varn = var.var
            td_vars[varn] = { 'dep':[], 'size':0, 'totsize':0 }
            td_vars[varn]['size'] =  var.size
            for dep in  var.get_dep():
                #Descend for that depend if it exists
                vers = dep.split('.')[2]
                if vers == "latest":
                    try:
                        dep = Var(dep, self.__AddonDir, use_db=True).latest()
                    except VarNotFound:
                        pass
                elif vers.startswith("min"):
                    try:
                        dep = Var(dep, self.__AddonDir, use_db=True).min()
                    except VarNotFound:
                        pass
                td_vars[varn]['dep'].append(dep)
                try:
                    if dep and Var(dep, self.__AddonDir, use_db=True).exists():
                        if dep == varn:
                            error(f"There is a recursion from {varn} to itself, avoiding")
                            continue
                        td_vars[varn]['totsize'] += Var(dep, self.__AddonDir, use_db=True).size
                        rec(Var(dep, self.__AddonDir, use_db=True))
                except VarNotFound:
                    pass

        td_vars = {}
        rec(self)
        return td_vars

    def dupinfo(self):
        """
        Returns dict about duplication of files with other creators vars
        """
        dups = { "numdupfiles": 0, "dupsize": 0 }

        for file in self.db_files(with_meta=False):
            if self.get_file_size(file) <= 4:
                continue

            ck = self.get_file_cksum(file)
            ckdup = self.db_fetch("SELECT VARNAME, FILENAME FROM FILES WHERE CKSUM == ? AND VARNAME != ?", (ck, self.var))

            ckdup_creator = []
            for v, f in ckdup:
                creator = VarFile(v, use_db=True).get_prop_vars("CREATOR")
                if creator != self.creator:
                    ckdup_creator.append((v, f))

            if ckdup_creator:
                dups['numdupfiles'] += 1
                dups['dupsize'] += self.get_file_size(file)
                for dupvar, dupfile in ckdup:
                    info(f"{self.var}:/{Path(file).name} is dup of {dupvar}:/{dupfile}")
        return dups

    def reref_files(self, newref):
        tdir = self.tmpDir
        for globf in search_files_indir(tdir, "*"):
            if globf.name == "meta.json" or globf.suffix in (".vmi", ".vam", ".vab", ".assetbundle", ".tif", ".jpg", ".png", ".dll"):
                continue
            try:
                file = FileName(globf)
                js = file.json
            except (UnicodeDecodeError, json.decoder.JSONDecodeError):
                continue
            debug(f"> Searching for pattern in {globf}")
            for nr in newref:
                replace_string = ""
                fs = ""
    #            info(f">> Applying reref for {nr}")
                with open(globf, 'r') as f:
                    fs = f.read()
                    rep = f"{newref[nr]['newvar']}:/{newref[nr]['newfile']}"
                    replace_string = self.ref_replace(nr, fs, rep)
                if replace_string != fs:
                    debug(f"In {globf.relative_to(self.tmpDir).as_posix()}, {nr} --> {rep}")
                    try:
                        _ = json.loads(replace_string)
                    except (UnicodeDecodeError, json.decoder.JSONDecodeError):
                        error("While rerefing, something went wrong as we are trying to write non json content")
                        critical(replace_string, doexit=True)
                    with open(globf, "w") as f:
                        f.write(replace_string)
                    debug(f"!! Rewrote {globf.relative_to(self.tmpDir)}")

    def ref_replace(self, nr, fs, rep):
        replace_string = fs.replace(f"\"SELF:/{nr}\"", f"\"{rep}\"").replace(f"\"/{nr}\"", f"\"{rep}\"")
        return replace_string

    def delete_files(self, newref):
        tdir = self.tmpDir
        for nr in newref:
            file = Path(tdir, nr)
            debug(f"!! Erased {file.relative_to(self.tmpDir)}")
            try:
                os.unlink(file)
            except FileNotFoundError:
                warn(f"File {file} not found in var {self.var}. Database is not up to date?")

    def modify_meta(self, newref):
        tdir = self.tmpDir
        meta = self.meta()
        for nref in newref:
            newvar = newref[nref]['newvar']
            meta["dependencies"][newvar]={}
            meta["dependencies"][newvar]['licenseType'] = Var(newvar, dir = self.addondir, use_db=True).license
            try:
                meta['contentList'].remove(nref)
            except ValueError:
                # The exact file was not mentionned in the contentList
                # TODO empty dirs from contentList
                pass
        with open(Path(tdir, "meta.json"), 'w') as f:
            f.write(prettyjson(meta))
        logging.debug("Modified meta")

    def get_new_ref(self, dup) -> dict:
        # Todo propose .latest in choices
        new_ref = {}
        var_already_as_ref = []
        for file in self.db_files(with_meta=False):
#            if Path(file).suffix in (".jpg", ".png", ".tif"):
#                continue
            if dup and Path(file).name != dup:
                continue
            choice = 0
            ref_var = self.get_refvar_forfile(file)
            if ref_var:
                if len(ref_var) > 1:
                    print(f"We got multiple original file for {file}")
                    auto = False
                    for count, rvar in enumerate(ref_var):
                        if not auto and rvar[0] in var_already_as_ref:
                            auto = True
                            choice = count
                        print(f"{count} : {rvar[0]}{' AUTO' if auto and choice == count else ''}")
                    if not auto:
                        try:
# TODO latest
                            choice_s = input("Which one to choose [ Enter to skip ] ?")
                            choice = int(choice_s)
                        except ValueError:
                            if not choice_s:
                                continue
                            choice = int(choice_s.rstrip("L"))
                            ref = ref_var[choice]
                            ref_var_latest = ".".join(ref[0].split('.')[0:2]) + ".latest"

                            var_already_as_ref.append(ref_var_latest)
                            new_ref[file] = {}
                            new_ref[file]['newvar'] = ref_var_latest
                            new_ref[file]['newfile'] = ref[1]
                            continue
                ref = ref_var[choice]
                var_already_as_ref.append(ref[0])
                new_ref[file] = {}
                new_ref[file]['newvar'] = ref[0]
                new_ref[file]['newfile'] = ref[1]
        new_ref = vmb_vmi(new_ref)

        for file in self.files():
            pre = file.path.relative_to(self.tmpDir).as_posix()
            if file in new_ref:
                debug(f"{ pre } : { green(new_ref[file]['newvar']) }{ green(':/') }{ green(new_ref[file]['newfile']) }")
            else:
                debug(f"{ red(pre) } {red(':')} { red('NO REFERENCE') }")
        return new_ref

    def reref(self, dryrun=True, dup=None):
        info(f"Searching for dups in {self.var}")
        if self.get_ref == "YES":
            debug(f"Asked to reref {self.var} but it is a reference var!")
#            return

        new_ref = self.get_new_ref(dup)
        if not new_ref:
            info("Found nothing to reref")
            return
        else:
            info(f"Found these files as duplicates:{','.join(list(new_ref))}")

        for nr in new_ref:
            print(f"{green(self.var):<20}: {nr} --> {green(new_ref[nr]['newvar'])}:/{new_ref[nr]['newfile']}")

        choice = input("Confirm [Enter: Skip, Y: to modify, S: skip creator]?").upper() 
        if not choice:
            return
        elif choice == "S":
            return C_NEXT_CREATOR
        elif choice != "Y":
            return

        if dryrun:
            info("Asked for dryrun, stopping here")
            return

        self.modify_meta(new_ref)
        self.reref_files(new_ref)
        self.delete_files(new_ref)
        try:
            del_empty_dirs(self.tmpDir)
        except:
            pass
        # TODO: remove any leaf element not having anything referencing them

        try:
            os.rename(self.path, f"{self.path.with_suffix('.orig')}")
        except:
            critical("We could not backup {self.path} to .orig, refusing to proceed for safety.", doexit=True)
        zipdir(self.tmpDir, self.path)

        print(green("Modified {self.path}"))
        self.store_update(confirm=False)
        info("Updated DB for {self.var}")
