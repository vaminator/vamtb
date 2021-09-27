from jinja2 import Environment, FileSystemLoader
import logging
from pathlib import Path
from zipfile import ZipFile

class Uiap:
    def __init__(self):
        pass

    @classmethod
    def gen_uia(self, **kwargs):
        file_loader = FileSystemLoader('vamtb/tpl')
        env = Environment(loader=file_loader)
        template = env.get_template('uiap.j2')

        output = template.render(**kwargs)
        return output

    @classmethod
    def get_gridlabel(self, txt):
        """
        Keep the SAME ORDER /!\
        """
        rtxt = txt
        rtxt = rtxt.replace('/',' ')
        rtxt = rtxt.replace('poses ','')
        rtxt = rtxt.replace(' poses','')
        rtxt = rtxt.replace('Poses ','')
        rtxt = rtxt.replace(' Poses','')
        rtxt = rtxt.replace('Klphgz ','')
        rtxt = rtxt.replace('Nial - ','')
        rtxt = rtxt.replace('[Alter3go] ','')
        rtxt = rtxt.replace('ZRSX - ','')
        rtxt = rtxt.replace('CosmicFTW - ','')
        rtxt = rtxt.replace('SupaRioAmateur ','')
        rtxt = rtxt.replace('REM ','')
        rtxt = rtxt.replace(' or sort of casual','')
        rtxt = rtxt.replace('400 ','')
        rtxt = rtxt.replace('POSE ','')
        rtxt = rtxt.replace('POSES ','')
        rtxt = rtxt.replace('FEMALE ','F ')
        rtxt = rtxt.replace('MALE ','M ')
        rtxt = rtxt.replace('SUPINE ','')

        rtxt = rtxt[0].upper() + rtxt[1:]
        if txt != rtxt:
            logging.info("Renaming button grid from %s to %s, will be displayed as %s" % (txt, rtxt, rtxt[0:15]))
        return rtxt

    @classmethod
    def gridsize(self, nf):
        """
        Fuzzy logic to determine optimal gridsize from full screen proportion
        """
        col_row = [ [2,2], [2,3], [3,2], [3,3], [3,4], [4,3], [4,4], 
        [4,5], [5,4], [5,5], [5,6], [6,5], [6,6], [7,6], [6,7], [7,7], [8,7], [7,8], [8,8], [9,8], [8,9], [9,9] ]
        c=9
        r=9
        for cr, rr in col_row:
            if cr * rr >= nf:
                c = cr
                r = rr
                break
        bsize="Large"
        if r>=6 and c>=6:
            bsize="Medium"
        if r>=5 and c>=6:
            bsize="Medium"
        if r>3 or c>3:
            bsize="Small"    
        return c, r, bsize

    @classmethod
    def fill_grid(self, grid):
        nf = len(grid['files'])
        c, r, bsize = self.gridsize(nf)
        npad = r * c  -nf
        for i in range(npad):
            grid['files'].append("")
        grid['bsize'] = bsize
        grid['col'] = c
        grid['row'] = r


    def uiap(self, varfile):
        lmax=7;cmax=6
        ngmax = 0
        logging.debug("Generating uia presets for %s" % varfile)
        based=Path("")
        for p in Path(varfile).parents:
            if p.stem == "AddonPackages":
                based = Path(p).parent
        grids = []
        lastdir = None
        ngrid = 0
        with ZipFile(varfile, 'r') as zin:
            for mfile in zin.infolist():
                if mfile.filename.startswith("Custom/Atom/Person/Pose/") and mfile.filename.endswith(".vap"):
                    vfile = Path(mfile.filename).name
                    posedir = mfile.filename[len("Custom/Atom/Person/Pose/"):-len(vfile)-1]
                    gridlabel = self.get_gridlabel(posedir)
                    if posedir != lastdir or len(grids[-1]['files']) == lmax * cmax:
                        if lastdir is not None:
                            self.fill_grid(grids[-1])
                        if ngmax and ngrid >= ngmax:
                            break
                        grids.append({"label": gridlabel, "files": []})
                        lastdir = posedir
                        ngrid += 1
                    grids[-1]['files'].append("/" + mfile.filename)
        self.fill_grid(grids[-1])
        uiap = self.gen_uia(varfile = varfile.name[:-4], grids = grids)
        with open("out.uiap", "w") as f:
            f.write(uiap)