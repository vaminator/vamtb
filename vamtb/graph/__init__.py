import logging 
from vamtb import db
import subprocess
import os
from vamtb.utils import *
from vamtb.varfile import VarFile

class Graph:
    __desc_deps=[]
    __asc_deps=[]
    __dbs=None

    def __init__(self, dbs=None):
        if not dbs:
            dbs = db.Dbs()
        Graph.__dbs = dbs

    def deps_desc_node(self, var, deep = True):
        """
        Returns vars on which var depends
        """
        uniq = set()

        sql="SELECT DISTINCT DEPVAR FROM DEPS WHERE VAR = ? COLLATE NOCASE"
        row = (var, )
        res = Graph.__dbs.fetchall(sql, row)
        # flatten tuple with 1 element
        res = [ e[0] for e in res ]
        for depvar in res:
            v = depvar.split('.')[2]
            if v == "latest":
                ldepvar = Graph.__dbs.latest(depvar)
                if ldepvar is not None:
                    depvar = ldepvar
            elif v.startswith("min"):
                ldepvar = Graph.__dbs.min(depvar)
                if ldepvar is not None:
                    depvar = ldepvar
            uniq.add(depvar)
        self.__desc_deps.extend(uniq)

        if deep:
            for dep in sorted([ v for v in uniq if v not in desc_deps ]):
                self.__desc_deps.extend(self.deps_desc_node(dep))
        return self.__desc_deps

    def deps_asc_node(self, var, deep=True):
        """
        Returns vars depending on var
        """
        sql = "SELECT DISTINCT VAR FROM DEPS WHERE DEPVAR = ? OR DEPVAR = ? COLLATE NOCASE"
        row = (f"{VarFile(var).var_nov}.latest", f"{var}")
        res = Graph.__dbs.fetchall(sql, row)
        # flatten tuple with 1 element
        res = [ e[0] for e in res ]

        asc = [ e for e in res if not e.endswith(".latest") or self.latest(e) == e ]
        self.__asc_deps.extend(set(asc))

        if deep:
            for ascx in sorted([ e for e in asc if e != var and e not in asc_deps ]):
                self.__asc_deps.extend(self.deps_asc_node(ascx))
        return set(self.__asc_deps)

    def deps_node(self, var):
        """Get dependent and ascendant nodes"""
        global asc_deps
        global desc_deps
        asc_deps=[]
        desc_deps=[]
        depd = set(self.deps_desc_node(var))
        depa = set(self.deps_asc_node(var))
        dep = {var} | depd | depa
        return sorted(dep, key=str.casefold)

    def set_props(self, var_list):
        res = []
        for var in var_list:
            res.append(f'"{var}" [color={"blue" if Graph.__dbs.var_exists(var) else "red"}];')
            license = Graph.__dbs.get_license(var)
            if license in ("PC", "Questionable"):
                res.append(f'"{var}" [shape=box];')
        return res

    def dotty(self, lvar=None):

        direct_graphs=[]
        shapes = []
        cmddot = "c:\\Graphviz\\bin\\dot.exe"

        if isinstance(lvar, os.PathLike):
            lvar = VarFile(lvar).var

        if lvar:
            only_nodes = self.deps_node(lvar)
            debug(f"only_nodes={only_nodes}")

        if lvar and not Graph.__dbs.var_exists(lvar):
            info(f"{lvar} not found in the database, run dbs subcommand?")
            return

        the_deps = Graph.__dbs.get_db_deps()
        debug(f"deps={the_deps}")

        for varv, depv in the_deps:
            dep = None
            var = None
            depvers = depv.split('.')[2]
            varvers = varv.split('.')[2]
            if depvers == "latest":
                dep = Graph.__dbs.latest(depv)
            if varvers == "latest":
                var = Graph.__dbs.latest(varv)
            if depvers.startswith("min"):
                dep = Graph.__dbs.min(depv)
            if varvers.startswith("min"):
                var = Graph.__dbs.min(varv)
            if not dep:
                dep = depv
            if not var:
                var = varv
            #FIXME we get more vars than the ones on the path
            if lvar and dep not in only_nodes and var not in only_nodes:
#            if lvar and lvar not in (dep, var):
                continue
            if f'"{var}" -> "{dep}";' not in direct_graphs:
                info(f"Adding {var} -> {dep}")
                props = self.set_props([var, dep])
                shapes.extend(props)
                direct_graphs.append(f'"{var}" -> "{dep}";')

        if direct_graphs:
            dot_lines = shapes 
            dot_lines.extend(sorted(list(set(direct_graphs))))

            with open("deps.dot", "w") as f:
                f.write("digraph vardeps {" + "\n" + 
                "\n".join(dot_lines) + "\n" + 
                "}")

            pdfname = f"VAM_{lvar}.pdf" if lvar else "VAM_deps.pdf"
            try:
                subprocess.check_call(f'{cmddot} -Gcharset=latin1 -Tpdf -o "{pdfname}" deps.dot')
            except Exception as CalledProcessError:
                error("You need graphviz installed and dot available in {cmddot}")
                os.unlink("deps.dot")
                exit(0)
            os.unlink("deps.dot")
            info("Graph generated")

        else:
            warning(f"No graph as no var linked to {lvar}")
