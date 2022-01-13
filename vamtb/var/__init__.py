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

from vamtb.file import FileName
from vamtb.varfile import VarFile

from vamtb.vamex import *
from vamtb.utils import *
from vamtb.log import *

class Var(VarFile):

    def __init__(self, multiFileName, dir=None, use_db = False, checkVar=False, check_exists = True):
        """
        multiFileName can be a.b.c, a.b.c.var, c:/tmp/a.b.c or c:/tmp/a.b.c.var
        in the two first cases, dir is required to find the var on disk
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

        if self._path.with_suffix(".jpg").exists():
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

    def check(self):
        self.zipcheck()
        metaj = self.meta()
        if "hadReferenceIssues" in metaj and metaj['hadReferenceIssues'] == "true":
            try:
                warn(f"{self.var} had {len(metaj['referenceIssues'])} references issues:\n{CR.join([e['reference'] for e in metaj['referenceIssues']])}")
            except KeyError:
                error(f"{self.var} had reference issues but no issue given, its likely that var was modified manually!")

        if self.tmpDir.exists() and not (
            Path(self.tmpDir / "Custom").exists() or 
            Path(self.tmpDir / "Saves").exists()):
            raise VarMalformed(self.var)

    def store_var(self)->None:
        self.check()
        super()._store_var()

    def store_update(self, confirm = True) -> bool:
        if self.exists():
            debug(f"{self.var} already in database")
            if FileName(self.path).mtime == self.get_modtime or FileName(self.path).crc == self.get_cksum:
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
        with ZipFile(self.path) as zipf:
            res = zipf.testzip()
            if res != None:
                critical(f"Zip {self.path} is corrupted, can't open file {res}.")
            else:
                info(f"Zip {self.path} is ok.")

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
            #self.__del__()
            critical(f"Var {self.var} has CRC problems.")
            raise
        else:
            self.__tmpDir = tmpPathdir
            debug(f"Extracted {self.var} to {self.__tmpDir}")

    def meta(self) -> dict:
        if not self._meta:
            try:
                self._meta = self.load_json_file("meta.json")
            except json.decoder.JSONDecodeError as e:
                critical(f"Meta.json from {self.var} is broken [{e}]", doexit=True)
                raise VarMetaJson(self.var)
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
            file = tdir / nr
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
            if "dependencies" not in meta:
                meta['dependencies'] = {}
            meta["dependencies"][newvar]={}
            meta["dependencies"][newvar]['licenseType'] = Var(newvar, dir = self.addondir, use_db=True).license
            try:
                meta['contentList'].remove(nref)
            except ValueError:
                # The exact file was not mentionned in the contentList
                pass
        with open(tdir / "meta.json", 'w') as f:
            f.write(prettyjson(meta))
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

    def reref(self, dryrun=True, dup=None):
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
            choice = input(blue("Confirm [Enter: Skip, Y: to modify, S: skip creator]? ")).upper() 
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
            critical(f"Warning, reconstructed zip {self.path} has CRC problem on file {res}.", doexit=True)

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
        title = self.var
        creator = self.creator
        license_url = get_license_url(self.license)
        if not license_url and only_cc:
            info('License is not CC')
            return False
        #
        choice = True
        if choice and input("Confirm [Y]N ?").upper() == "N":
            error("Cancelled")
            return

        types = self.get_resources_type()
        identifier = ia_identifier(self.var, iaprefix)

        if not self.exists():
            critical(f"Var {self.var} is not in the database. Can't upload to IA.")
            return False

        if not meta_only and self.latest() != self.var:
            warn(f"Not uploading {self.var}, there is a higher version {self.latest()}")
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

        description = f"<div><i>{self.var}</i></div><br />"
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
            if input(f"Item {self.var} exists, update if different Y [N] ? ").upper() != "Y":
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
                return True
            else:
                return False

    def anon_upload(self, apikey, dry_run = False):
        info(f"Uploading {self.var} [size {toh(self.size)}] to Anonfiles")
        url = f"https://api.anonfiles.com/upload?token={apikey}"
        if dry_run: 
            print(f"Would upload\n{self.path}")
            return False
        else:
            r =  requests.post(url, files={'file': open(self.path, 'rb')})
            j = r.json()
            if r.status_code == 200:
                print(f"{self.var} upload to Full url: {j['data']['file']['url']['full']}, Short url: {j['data']['file']['url']['short']}")
                return True
            else:
                error(f"Anonfiles gave response:{j}")
                return False

