'''Var file naming'''
import json
import os
import re
import shutil
import tempfile
import json
import time
import requests
from pathlib import Path
from zipfile import ZipFile
from internetarchive import get_item
from PIL import Image, ImageFile

from vamtb.file import FileName
from vamtb.varfile import VarFile

from vamtb.vamex import *
from vamtb.utils import *
from vamtb.log import *

class Var(VarFile):

    def __init__(self, multiFileName, dir=None, use_db = False, checkVar=False, check_exists = True, check_file_exists=True, check_naming=True):
        """
        multiFileName can be a.b.c, a.b.c.var, c:/tmp/a.b.c or c:/tmp/a.b.c.var
        in the two first cases, dir is required to find the var on disk
        """
        # tempdir to extracted var
        multiFileName or critical("Tried to create a var but gave no filename")
    
        self.__tmpDir = None
        VarFile.__init__(self, multiFileName, use_db, check_naming)

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

        # Password for extracting zip (only for renamevar)
        self.__password = None

        # Verify and resolve var on disk
        if check_file_exists:
            self._path = Path(self.__resolvevar(multiFileName))
        else:
            self._path = None

        if self._path and self._path.with_suffix(".jpg").exists():
            self.__thumb = self.path.with_suffix(".jpg")

        debug(f"Var {multiFileName} is found as {self._path}")

        if use_db and check_exists:
            if self.exists():
                debug(f"Var is in DB")
            else:
                warn(f"{self.var} at {self.path} is not in DB, run dbscan.")
        
        if checkVar:
            self.check()

    @property
    def path(self) -> str:
        return self._path

    @property
    def get_zipinfolist(self):
        return ZipFile(self.path).infolist()

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
    def fsize(self):
        ssz = os.stat(self.path).st_size
        return ssz
    
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
            try:
                self.__tmpTempDir.cleanup()
            except AttributeError:
                # We didn't unpack ourselves
                pass

    def check(self):
        if not self.zipcheck():
            raise VarMalformed("Zip is corrupted")
        metaj = self.meta()
        if "hadReferenceIssues" in metaj and metaj['hadReferenceIssues'] == "true":
            try:
                warn(f"{self.var} had {len(metaj['referenceIssues'])} references issues:\n{CR.join([e['reference'] for e in metaj['referenceIssues']])}")
            except KeyError:
                error(f"{self.var} had reference issues but no issue given, its likely that var was modified manually!")

        if self.tmpDir.exists() and not (
            Path(self.tmpDir / "Custom").exists() or 
            Path(self.tmpDir / "Saves").exists()):
            raise VarMalformed("Contains neither Custom nor Saves dir")

    def store_var(self)->None:
        self.check()
        super()._store_var()

    def store_update(self, confirm = True) -> bool:
        if self.exists():
            debug(f"{self.var} already in database")
            if FileName(self.path).mtime == self.get_modtime:
                info("Same modtime")
                return False
            info(f"Database is not inline.")
            if confirm == False:
                res = "Y"
            else:
                #TODO don't allow anything else than Enter, Y, N
                res = input(blue(f"Remove older DB for {self.path} [Y]N  ?"))
            if not res or res == "Y":
                self.db_delete() 
                self.db_commit()
            else:
                self.db_commit(rollback = True)
                return False
        self.store_var()
        return True

    def zipcheck(self):
        is_ok = False
        try:
            with ZipFile(self.path) as zipf:
                res = zipf.testzip()
                if res != None:
                    critical(f"Zip {self.path} is corrupted, can't open file {res}.")
                else:
                    info(f"Zip {self.path} is ok.")
                    is_ok = True
        except Exception as e:
            pass
        return is_ok

    def search(self, pattern)-> Path:
        return search_files_indir2(self.__AddonDir, pattern)

    def __resolvevar(self, multiname):
        """This will return the real var as an existing Path"""
        #debug(f"__resolvar({multiname})")
        for p in (multiname, f"{multiname}.var", f"{self.__AddonDir}/{multiname}", f"{self.__AddonDir}/{multiname}.var"):
            if Path(p).exists() and Path(p).is_file():
                return Path(p)

        # Not a full path var, search var on disk
        if self.version == "latest" or self.minversion:
            pattern = re.escape(self.creator) + "\." + re.escape(self.resource) + "\..*\.var"
        elif self.iversion != -1:  #TODO was that supposed to arrive?
            pattern = self.file
        else:
            raise VarNotFound(multiname)

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
            debug(f"Extracting zip {self.var} to {tmpPathdir}")
            with ZipFile(self.path) as z:
                if self.__password:
                    z.setpassword(self.__password.encode('utf-8'))
                z.extractall(tmpPathdir)
            debug(f"Extracting done...")
        except Exception as e:
            #self.__del__()
            critical(f"Var {self.var} has problems unpacking {e}.")
            raise
        else:
            self.__tmpDir = tmpPathdir
            debug(f"Extracted {self.var} to {self.__tmpDir}")

    def meta(self) -> dict:
        if not self._meta:
            try:
                self._meta = self.load_json_file("meta.json")
            except json.decoder.JSONDecodeError as e:
                raise VarMetaJson(e)
            except FileNotFoundError as e:
                raise NoMetaJson(self.var)
        return self._meta

    @property
    def tmpDir(self):
        return self.__tmpDir

    def set_password(self, password):
        self.__password = password

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
        return FileName(self.__tmpDir / filename).json

    @unzip
    def open_file(self, fname):
        fn = FileName(self.__tmpDir / fname)
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
        """
        Print depends based on json
        """
        global depend_node

        # For dependency loop tracking, init nodes
        info(f"Checking dep of {self.var}")
        if init:
            depend_node = [ self.var ]
        for dep in sorted(self.dep_fromfiles()):
            if dep not in depend_node:
                depend_node.append(dep)
                try:
                    with  Var(dep, self.__AddonDir) as var:
                        debug(f"{self.var} depends on {var}")
                        if recurse:
                            var.depend(recurse=True, init = False, check = check)
                except VarNotFound as e:
                    if check:
                        warn(f"{dep} Not found")
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
            creator_dir = self.creator
            for ca in C_CREATORS_ALIAS:
                if self.creator in C_CREATORS_ALIAS[ca]:
                    creator_dir = ca
                    break

            newpath = self.__AddonDir / creator_dir / file_to_move.name

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
                debug(f"Exact same file exists, removing duplicate {self.path}")
                try:
                    Path.unlink(file_to_move)
                except PermissionError:
                    error(f"Couldnt remove {file_to_move}")
            else:
                error(f"File {file_to_move} and {newpath} have same name but crc differ {fcrc} vs {ncrc}. Remove yourself.") 

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
                tvar = VarFile(v, use_db=True)
                if not( tvar.creator == self.creator and tvar.resource == self.resource ):
                    ckdup_creator.append((v, f))

            if ckdup_creator:
                dups['numdupfiles'] += 1
                dups['dupsize'] += self.get_file_size(file)
                for dupvar, dupfile in ckdup:
                    info(f"{self.var}:/{file} is dup of {dupvar}:/{dupfile}")
            else:
                info(f"No dup for {self.var}:/{file}")
        return dups

    def opt_image(self, fname, optlevel):
        """
            1 (1-bit pixels, black and white, stored with one pixel per byte)
            L (8-bit pixels, black and white)
            P (8-bit pixels, mapped to any other mode using a color palette)
            RGB (3x8-bit pixels, true color)
            RGBA (4x8-bit pixels, true color with transparency mask)
        """
        fname = str(Path(fname).as_posix())
        # Use a temp image for reading
        old_image = str(Path(fname).with_suffix(".orig"))
        osize = FileName(fname).size
        shutil.copyfile(fname, old_image)
        picture = Image.open(old_image)
        debug(f"Image mode is : {red(picture.mode)}")
        if optlevel:
            if picture.mode in ("RGBA", "P", "I"):
                warn(f"Image {fname} is of mode {picture.mode} and we'll convert it to RGB")
                picture = picture.convert("RGB")
            new_image = str(Path(fname).with_suffix(".jpg"))
            jpeg_qual = 90 if optlevel == 1 else 75
        else:
            jpeg_qual = "keep"
            new_image = fname

        pfname = os.path.relpath(fname, self.__tmpDir)
        pdname = os.path.relpath(new_image, self.__tmpDir)
        # Conversion of png to jpg ?
        has_changed_format = True if fname != new_image else False
        picture.save(new_image, optimize = True, quality = jpeg_qual, compress_level=9, progressive=False)
        nsize = FileName(new_image).size
        persize = int(100*(1-nsize/osize))
        info(f"Level {optlevel} - JPEG qual {jpeg_qual} => {red(str(persize)+'% less')}\n{green(pfname+'->'+pdname)}")
        os.unlink(old_image)
        # We converted from png to jpg, remove old png
        if has_changed_format:
            os.unlink(fname)
        return has_changed_format

    backed = False
    optimized = {}
    def opt_images(self, json_file, optlevel):
        """
        optlevel: 0 => lossless
        optlevel: 1 => convert to 90% Jpg
        optlevel: 2 => convert to 75% Jpg
        """

        minsize = 1024*1024*5  # 5MB
        global backed
        global optimized

        with open(json_file, 'r') as f:
            json_content = f.read()
        if optlevel:
            pattern = re.compile(r'(".+") : (?:"SELF:/(.+(?:jpg|png)))', re.IGNORECASE)
        else:
            pattern = re.compile(r'(".+") : (?:"SELF:/(.+(?:png)))', re.IGNORECASE)
        for m in re.finditer(pattern, json_content):

            # Don't optimized files aready optimized 
            if m.group(2) in optimized:
                continue
            else:
                optimized[m.group(2)] = True

            img = FileName(f"{self.tmpDir}\{m.group(2)}")
            debug(f">> {m.group(1)} image {m.group(2)} ")
            if img.size > minsize:
                if backed == False:
                    #Backups are for sissies
                    #if Path(self.path).with_suffix(".orig").exists():
                    #    critical(f"File {Path(self.path).with_suffix('.orig')} already exists, remove backup")
                    #shutil.copyfile(self.path, Path(self.path).with_suffix('.orig'))
                    backed = True
                # We default to conversion
                l_optlevel = optlevel
                if "Normal" in m.group(1) or "Decal" in m.group(1):
                    # TODO
                    # If that's a normal, we don't want to convert to jpg
                    # If that's a decal, it should have transparency (png mode) and we shouldn't convert to RGB
                    # For other png which don't require transparency, we should be able to convert to RGB and gain a lot
                    l_optlevel = 0
                debug(f">> size {toh(img.size)}, loss_level={l_optlevel}")
                has_changed_format = self.opt_image(f"{self.tmpDir}\{m.group(2)}", l_optlevel)
                if has_changed_format:
                    debug(f"Replacing with {str(Path(m.group(2)).with_suffix('.jpg').as_posix())}")
                    replace_string = json_content.replace(m.group(2), str(Path(m.group(2)).with_suffix(".jpg").as_posix()))
                    with open(json_file, "w") as f:
                        f.write(replace_string)
        return backed


    @unzip
    def var_opt_images(self,opt_level):
        global backed
        global optimized
        backed = False
        optimized = {}
        modified_var = False
        tdir = self.tmpDir
        ImageFile.MAXBLOCK = 2**20
        osize = self.size
        for globf in search_files_indir(tdir, ".*"):
            if globf.name == "meta.json" or globf.suffix in (".vmi", ".vam", ".vab", ".assetbundle", ".scene", ".tif", ".jpg", ".png", ".dll"):
                continue
            if not Path(globf).is_file():
                continue
            try:
                file = FileName(globf)
                js = file.json
            except (UnicodeDecodeError, json.decoder.JSONDecodeError):
                continue
            debug(f"> Searching for images in {green(str(globf.relative_to(self.__tmpDir)))}")
            modified_var = self.opt_images(globf, opt_level)

        if modified_var:
            sopt_level={0: "tc_lossless", 1: "tc_nearlossless", 2: "tc_good"}
            nresource = f"{self.resource}_{sopt_level[opt_level]}"
            nvar = f"{self.creator}.{nresource}.{self.version}"

            # Create new var
            new_var = Var(nvar, dir = self.addondir, use_db=True, check_exists=False, check_file_exists=False)
            new_var._path = str(Path(new_var.addondir, f"{nvar}.var"))

            ometa = self.meta()
            ometa['packageName'] = nresource
            new_var.__tmpDir = tdir
            self.write_meta(tdir, ometa)

            zipdir(tdir, new_var.path)
            
            #Check it
            res = ZipFile(new_var.path).testzip()
            if res != None:
                critical(f"Warning, reconstructed zip {new_var.path} has CRC problem on file {res}.")
            
            warn(f"Modified {new_var.path}")
            new_var.store_update(confirm=False)
            info(f"Updated DB for {new_var.var}")
            
            nsize = new_var.size
            persize = int(100*(1-nsize/osize))
            warn(f"{toh(osize)}->{toh(nsize)}: {persize}% less")

    def reref_files(self, newref):
        tdir = self.tmpDir
        for globf in search_files_indir(tdir, "*"):
            if globf.name == "meta.json" or globf.suffix in (".vmi", ".vam", ".vab", ".assetbundle", ".scene", ".tif", ".jpg", ".png", ".dll"):
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
                #info(f">> Applying reref for {nr}")
                with open(globf, 'r') as f:
                    fs = f.read()
                    rep = f"{newref[nr]['newvar']}:/{newref[nr]['newfile']}"
                    replace_string = self.ref_replace(nr, fs, rep)
                if replace_string != fs:
                    debug(f"In {globf.relative_to(self.tmpDir).as_posix()}, {nr} --> {rep}")
                    try:
                        _ = json.loads(replace_string)
                    except (UnicodeDecodeError, json.decoder.JSONDecodeError) as e:
                        error(f"While rerefing, something went wrong as we are trying to write non json content\n{e}")
                        critical(replace_string)
                    with open(globf, "w") as f:
                        f.write(replace_string)
                    debug(f"!! Rewrote {globf.relative_to(self.tmpDir)}")

    def ref_replace(self, nr, fs, rep):
        replace_string = fs.replace(f"\"SELF:/{nr}\"", f"\"{rep}\"").replace(f"\"/{nr}\"", f"\"{rep}\"")
        return replace_string

    def delete_files(self, newref):
        tdir = self.tmpDir
        for nr in newref:
            file = tdir / nr
            debug(f"!! Erased {file.relative_to(self.tmpDir)}")
            try:
                os.unlink(file)
            except FileNotFoundError:
                warn(f"File {file} not found in var {self.var}. Database is not up to date?")

    def write_meta(self, tdir, mdict: dict):
        with open(tdir / "meta.json", 'w') as f:
            f.write(prettyjson(mdict))

    def modify_meta(self, newref):
        tdir = self.tmpDir
        meta = self.meta()
        for nref in newref:
            newvar = newref[nref]['newvar']
            if "dependencies" not in meta:
                meta['dependencies'] = {}
            meta["dependencies"][newvar]={}
            meta["dependencies"][newvar]['licenseType'] = Var(newvar, dir = self.addondir, use_db=True).license
            try:
                meta['contentList'].remove(nref)
            except ValueError:
                # The exact file was not mentionned in the contentList
                pass

        self.write_meta(tdir, meta)
        debug("Modified meta")

    def get_new_ref(self, dup) -> dict:
        # Todo propose .latest in choices
        new_ref = {}
        var_already_as_ref = []
        for file in self.db_files(with_meta=False):
            #if Path(file).suffix in (".jpg", ".png", ".tif"):
                #continue
            if dup and Path(file).name != dup:
                continue
            choice = 0
            ref_var = self.get_refvar_forfile(file)
            if ref_var:
                if len(ref_var) > 1:
                    print(f"We got multiple original file for {green(self.var)}:{file}")
                    ref_var_varname = [ e[0] for e in ref_var ]
                    inter_var = set(var_already_as_ref) & set(ref_var_varname)
                    auto = False
                    for count, rvar in enumerate(ref_var):
                        if not auto and rvar[0] in var_already_as_ref and len(inter_var) == 1:
                            auto = True
                            choice = count
                        print(f"{count} : {green(rvar[0])}{' AUTO' if auto and choice == count else ''}")
                    if not auto:
                        ref = None
                        next_file = False
                        while not next_file:
                            try:
                                try:
                                    # TODO propose latest?
                                    choice_s = input(blue("Which one to choose [ Enter: skip file, S: Skip var ] ? ")).upper()
                                    choice = int(choice_s)
                                except ValueError:
                                    if not choice_s:
                                        next_file = True
                                        continue
                                    elif choice_s == "S":
                                        return
                                    choice = int(choice_s.rstrip("L"))
                            except (ValueError, IndexError) :
                                error("Wrong answer..")
                                pass
                            else:
                                break
                        if next_file:
                            continue
                ref = ref_var[choice]
                var_already_as_ref.append(ref[0])
                new_ref[file] = {}
                new_ref[file]['newvar'] = ref[0]
                new_ref[file]['newfile'] = ref[1]

        for ftype in ("vmi", "vam", "vap", "vaj"):
            new_ref = ensure_binaryfiles(new_ref, ftype)

        for file in self.files():
            pre = file.path.relative_to(self.tmpDir).as_posix()
            if file in new_ref:
                debug(f"{ pre } : { green(new_ref[file]['newvar']) }{ green(':/') }{ green(new_ref[file]['newfile']) }")
            else:
                debug(f"{ red(pre) } {red(':')} { red('NO REFERENCE') }")
        return new_ref

    def reref(self, dryrun=True, dup=None, confirm=True):
        info(f"Searching for dups in {self.var}")
        if self.get_ref == "YES":
            debug(f"Asked to reref {self.var} but it is a reference var!")
            #return

        new_ref = self.get_new_ref(dup)
        if not new_ref:
            info("Found nothing to reref")
            return
        else:
            info(f"Found these files as duplicates:{','.join(list(new_ref))}")

        for nr in new_ref:
            print(f"{green(self.var):<20}:/{nr} --> {green(new_ref[nr]['newvar'])}:/{new_ref[nr]['newfile']}")

        #TODO print which var relied on these files
        #TODO choice for selectively taking/removing reref for a set of files
        #TODO don't remove a jpg if all the rest (vam, vaj and vab) are kept. Otherwise that leads to white icons in clothing list..

        while True:
            if confirm:
                choice = input(blue("Confirm [Enter: Skip, Y: to modify, S: skip creator]? ")).upper() 
            else:
                break
            if not choice:
                return
            elif choice == "S":
                return C_NEXT_CREATOR
            elif choice == "Y":
                break
            else:
                error("Wrong answer..")

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
        # TODO remove any leaf element not having anything referencing them

        try:
            os.rename(self.path, f"{self.path.with_suffix('.orig')}")
        except:
            critical(f"We could not backup {self.path} to .orig, refusing to proceed for safety.")
            return

        zipdir(self.tmpDir, self.path)
        res = ZipFile(self.path).testzip()
        if res != None:
            critical(f"Warning, reconstructed zip {self.path} has CRC problem on file {res}.")

        print(green(f"Modified {self.path}"))
        self.store_update(confirm=False)
        print(green(f"Updated DB for {self.var}"))

    @unzip
    def get_thumbs(self)->str:
        thumbs = []
        custom_bin = search_files_indir(self.tmpDir / "Custom", "*.vap", ign=True) + search_files_indir(self.tmpDir / "Custom", "*.vaj", ign=True)
        custom_asset = search_files_indir(self.tmpDir / "Custom", "*.assetbundle", ign=True)
        custom_asset_2 = search_files_indir(self.tmpDir / "Custom", "*.scene", ign=True)
        old_json = search_files_indir(self.tmpDir, "*.json", ign=True)
        for v in custom_bin + custom_asset + custom_asset_2 + old_json:
            if v.with_suffix(".jpg").exists():
                thumbs.append(v.with_suffix(".jpg"))
        return [ str(e) for e in list(set(thumbs)) ]

    @unzip
    def get_resources_type(self):
        types = []
        if search_files_indir(self.tmpDir / "Saves" / "scene", "*.jpg", ign=True):
            types.append("scene")
        if search_files_indir(self.tmpDir / "Custom" / "Clothing", "*.vaj", ign=True):
            types.append("clothes")
        if search_files_indir(self.tmpDir / "Custom" / "Hair", "*.vaj", ign=True):
            types.append("hairs")
        if search_files_indir(self.tmpDir / "Custom" / "Assets", "*.assetbundle", ign=True):
            types.append("asset")
        if search_files_indir(self.tmpDir / "Custom" / "Assets", "*.scene", ign=True):
            types.append("asset")
        return types

    def ia_upload(self, confirm = True, meta_only = False, verbose = False, dry_run = False, full_thumbs = False, only_cc = False, iaprefix=None):

        info(f"Uploading {self.var} [size {toh(self.size)}] to IA")
        if self.is_uploaded_on_ia:
            info(f"{self.var} already on IA, not uploading")
            return

        title = self.var
        creator = self.creator
        license_url = get_license_url(self.license)
        if not license_url and only_cc:
            info('License is not CC')
            return False
        #
        print(f"Uploading {self}, {int(self.size/1000)/1000}MB")
        choice = False
        mchoice = "N"
        if choice:
            mchoice = input("Confirm [Y]ND ?").upper()
            if mchoice == "N":
                error("Cancelled")
                return
            elif mchoice == "D":
                error("Will not ask anymore")
                self.ia_set_uploaded()
                return

        types = self.get_resources_type()
        identifier = ia_identifier(self.varq, iaprefix or IA_IDENTIFIER_PREFIX)

        if not self.exists():
            critical(f"Var {self.var} is not in the database. Can't upload to IA.")
            return False

        if not meta_only and self.latest() != self.var:
            info(f"Not uploading {self.var}, there is a higher version {self.latest()}")
            self.ia_set_uploaded()
            return False

        if not license_url:
            warn(f"License is {self.license}, no URL.")

        thumbs = self.get_thumbs()
        if not thumbs:
            warn(f"No thumbs, not uploading.")
            return False

        debug(f"var {self.var} contains: {types}")
        subjects = ['scene'] if "scene" in types else types
        subjects.extend(IA_BASETAGS)

        description = f"<div><i>{self.varq}</i></div><br />"
        f"<div><br />By {creator}<br /></div>"
        f"<div><br />{self.meta()['description']}<br /></div>"
        f"<div><br /> <a href=\"{self.meta()['promotionalLink']}\">{creator}</a> <br /></div>"

        md = {
            'title': title,
            'mediatype' : IA_MEDIATYPE,
            'collection': IA_COLL,
            'date': time.strftime("%Y-%m-%d", time.gmtime(self.mtime)),
            'description': description,
            'subject': subjects,
            'creator': creator,
            'licenseurl': license_url
        }

        iavar = get_item(identifier)
        
        # Meta only: no overwrite confirmation
        if not meta_only and confirm and (iavar.exists or not iavar.identifier_available()):
            self.ia_set_uploaded()
            if input(f"Item {self.var} exists, update if different Y [N] ? ").upper() != "Y":
                self.ia_set_uploaded()
                return False
        if meta_only:
            if iavar.exists:
                debug(f"Modifying metadata for {identifier}")
                # Clear subject
                if dry_run:
                    return True
                else :
                    res = iavar.modify_metadata(metadata = { "subject": "REMOVE_TAG" })
                    if res:
                        info("Subject and topics cleared")
                    else:
                        warn(f"Subject was not changed: {res.content}")
                    res = iavar.modify_metadata(metadata = { "subject": subjects }, append=True)
                    if res:
                        info(f"Subject and topics set to {subjects}")
                    else:
                        error(f"Subject was not set: {res.content}")
                    return res.status_code == 200 if not dry_run else True
            else:
                warn("Item does not exists on IA, can't update metadata")
                return False
        else:
            scene_thumbs = search_files_indir(self.tmpDir / "Saves" / "scene", "*.jpg", ign=True)

            if full_thumbs or not scene_thumbs:
                files = thumbs
            else:
                files = []

            files.append(str(self.path))


            # Remove scene thumbs from files
            scene_thumbs_fn = [ str(e) for e in scene_thumbs ]
            files = [ e for e in files if e not in scene_thumbs_fn ]

            ok_s = True
            if scene_thumbs:
                scene_files = { "00-" + e.name:str(e) for e in scene_thumbs }
                if dry_run:
                    print(f"Would upload:\n{CR.join([Path(a).as_posix() for a in scene_files])}")
                    ok_s = False
                else:
                    res_s = iavar.upload(
                        validate_identifier=True,
                        checksum=True,
                        verify=True,
                        files = scene_files,
                        metadata=md,
                        verbose=verbose)
                    debug(res_s)
                    ok_s = all(resp.status_code == 200 or resp.status_code == None for resp in res_s)

            if not dry_run:
                res = iavar.upload(
                    validate_identifier=True,
                    checksum=True,
                    verify=True,
                    files = files,
                    metadata=md,
                    verbose=verbose)
                debug(res)
            else:
                print(f"Would upload:\n{CR.join([Path(a).as_posix() for a in files])}")
                return False
            # Upload will return empty Response() when checksum match. BAD
            if ok_s and all(resp.status_code == 200 or resp.status_code == None for resp in res):
                print(f"Var file url is https://archive.org/download/{ia_identifier(self.var)}/{self.file}")
                self.ia_set_uploaded()
                return True
            else:
                return False

    def anon_upload(self, apikey, dry_run = False):
        info(f"Uploading {self.var} [size {toh(self.size)}] to Anonfiles")
        if self.is_uploaded_on_anon:
            info(f"{self.var} already on anonfiles, not uploading")
            return

        url = f"https://api.anonfiles.com/upload?token={apikey}"
        if dry_run: 
            print(f"Would upload\n{self.path}")
            return False
        else:
            r =  requests.post(url, files={'file': open(self.path, 'rb')})
            j = r.json()
            if r.status_code == 200:
                print(f"{self.var} upload to Full url: {j['data']['file']['url']['full']}, Short url: {j['data']['file']['url']['short']}")
                self.anon_set_uploaded()
                return True
            else:
                error(f"Anonfiles gave response:{j}")
                return False

    def get_dep(self):
        sql = f"SELECT DISTINCT DEPVAR FROM DEPS WHERE VAR=?"
        row = (self.latest(),)
        res = self.db_fetch(sql, row)
        res = sorted([ e[0] for e in res ], key = lambda s: s.casefold())
        return res

    def get_rdep(self):
        sql = f"SELECT DISTINCT VAR FROM DEPS WHERE DEPVAR=?"
        row = (self.latest(),)
        res = self.db_fetch(sql, row)
        res = sorted([ e[0] for e in res ], key = lambda s: s.casefold())
        return res

    def rec_dep(self, stop = True, dir=None, func = None):
        def rec(var:Var, depth=0):
            msg = ">" * (depth+1) + f" {var.var}"
            if not var.exists():
                warn(f"{msg:<130}" + ": Not Found")
                if stop:
                    raise VarNotFound(var.var)
                return
            else:
                info(f"{msg:<130}" + ":     Found")
            res = var.get_dep()
            info(f"Found {len(res) if len(res) else 'no'} dependencies for {var.var}{', searching their own dependencies' if len(res) else ''}")
            for varfile in res:
                try:
                    if dir == None:
                        depvar = VarFile(varfile, use_db=True)                        
                    else:
                        try:
                            depvar = Var(varfile, dir=dir, use_db=True)
                        except VarNotFound as e:
                            if stop:
                                raise VarNotFound(varfile.var)
                            else:
                                error(f"Var {varfile} not found")
                                continue
                    if func:
                        func(depvar)
                except (VarExtNotCorrect, VarNameNotCorrect, VarVersionNotCorrect):
                    error(f"We skipped a broken dependency from {self.var}")
                    continue
                rec(depvar, depth+1 )
        rec(self)

