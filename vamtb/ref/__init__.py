import os
from vamtb.file import FileName
from vamtb.vamex import *
from vamtb.utils import *
from vamtb.log import *
from vamtb.varfile import Var
from vamtb.db import Dbs

def add_dependency():
    pass

def vmb_vmi(refi):
    refo = {}
    for fn in refi:
        if fn.endswith(".vmi"):
            fnb = fn[0:-1] + "b"
            if fnb not in refi:
                warn(f"We found a reference for {fn} but not its counterpart {fnb}")
                continue
            refo[fn] = refi[fn]
            refo[fnb] = refi[fnb]
        elif fn.endswith(".vmb"):
            fni = fn[0:-1] + "i"
            if fni not in refi:
                warn(f"We found a reference for {fn} but not its counterpart {fni}")
                continue
            refo[fn] = refi[fn]
            refo[fni] = refi[fni]
        else:
            refo[fn] = refi[fn]
    return refo

def modify_files(var, newref):
    tdir = var.tmpDir
    for globf in search_files_indir(tdir, "*"):
        if globf.name == "meta.json" or globf.suffix in (".vmi", ".vam", ".vab", ".assetbundle", ".tif", ".jpg", ".png", ".dll"):
            continue
        try:
            file = FileName(globf)
            js = file.json
        except:
            #Not a json file
            continue
        info(f"> Searching for pattern in {globf}")
        for nr in newref:
#            info(f">> Applying reref for {nr}")
            with open(globf, 'r+') as f:
                fs = f.read()
                rep = f"{newref[nr]['newvar']}:/{newref[nr]['newfile']}"
                replace_string = fs.replace(f"SELF:/{nr}", rep).replace(f"/{nr}", rep)
                if replace_string != fs:
                    info(f">>> Rerefing {globf} for {nr} to point to {rep}")
                    f.seek(0)
                    f.write(replace_string)

def delete_files(var:Var, newref):
    tdir = var.tmpDir
    for nr in newref:
        file = Path(tdir, nr)
        debug(f"Erasing {file}")
        os.unlink(file)

def modify_meta(var:Var, newref):
    tdir = var.tmpDir
    meta = var.meta()
    for nref in newref:
        newvar = newref[nref]['newvar']
        meta["dependencies"][newvar]={}
        meta["dependencies"][newvar]['licenseType'] = Dbs.get_license(newvar)
        meta['contentList'].remove(nref)
    with open(Path(tdir, "meta.json"), 'w') as f:
        f.write(prettyjson(meta))
    logging.debug("Modified meta")

def reref_var(var:Var, dryrun=True):
    new_ref = {}
    var_already_as_ref = []
    info(f"Searching for dups in {var}")
    if Dbs.get_ref(var.var) == "YES":
        warn(f"Asked to reref {var} but it is a reference var, not doing anything.")
        return
    for file in Dbs.get_files(var.var):
        debug(f"Checking if {file} has a reference candidate")
        choice = 0
        ref_var = Dbs.get_refvar_forfile(file, var.var)
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
                    choice = int(input("Which one to choose?"))
            ref = ref_var[choice]
            var_already_as_ref.append(ref[0])
            new_ref[file] = {}
            new_ref[file]['newvar'] = ref[0]
            new_ref[file]['newfile'] = ref[1]
    new_ref = vmb_vmi(new_ref)
    if not new_ref:
        info("Found nothing to reref")
        return
    else:
        info(f"Found these files as duplicates:{','.join(list(new_ref))}")
    if dryrun:
        info("Asked for dryrun, stopping here")
    else:
        modify_meta(var, new_ref)
        modify_files(var, new_ref)
        delete_files(var, new_ref)
        zipdir(var.tmpDir, var.file)
