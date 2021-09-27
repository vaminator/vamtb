import logging 
from vamtb import db
import subprocess
import os

class Graph:
    __desc_deps=[]
    __asc_deps=[]
    __dbs=None

    def __init__(self, dbs=None):
        if not dbs:
            dbs = db.Dbs()
        Graph.__dbs = dbs

    def deps_desc_node(self, var):
        uniq = set()

        sql="SELECT DEP FROM DEPS WHERE VAR = ? COLLATE NOCASE"
        row = (var, )
        res = Graph.__dbs.fetchall(sql, row)

        for depvar in [ e[0].split(':')[0] for e in res ]:
            if "latest" in depvar:
                ldepvar = Graph.__dbs.latest(depvar)
                if ldepvar is not None:
                    depvar = ldepvar
            uniq.add(depvar)
        self.__desc_deps.extend(uniq)

        for dep in sorted([ v for v in uniq if v not in desc_deps ]):
            self.__desc_deps.extend(self.deps_desc_node(dep))
        return self.__desc_deps

    def deps_asc_node(self, var):
        sql = "SELECT DISTINCT VAR FROM DEPS WHERE DEP LIKE ? OR DEP LIKE ? COLLATE NOCASE"
        var_nov = ".".join(var.split('.')[0:2])
        row = (f"{var_nov}.latest:%", f"{var}:%")
        res = Graph.__dbs.fetchall(sql, row)

        asc = [ e[0] for e in res ]
        asc = [ e for e in asc if not e.endswith(".latest") or self.latest(e) == e ]
        self.__asc_deps.extend(set(asc))

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
        
        if lvar:
            only_nodes = self.deps_node(lvar)

        if lvar and not Graph.__dbs.var_exists(lvar):
            logging.info(f"{lvar} not found in the database, run dbs subcommand?")
            return

        the_deps = Graph.__dbs.get_db_deps()
        for var, depf in the_deps:
            dep = None
            if "latest" in depf:
                dep = ".".join(depf.split(".", 2)[0:2])
                dep = Graph.__dbs.latest(dep)
            if not dep:
                dep = depf.split(':',1)[0]
            if lvar and not(dep in only_nodes and var in only_nodes):
                continue
            if f'"{var}" -> "{dep}";' not in direct_graphs:
                logging.debug(f"Adding {var} -> {dep}")
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
                logging.error("You need graphviz installed and dot available in {cmddot}")
                os.unlink("deps.dot")
                exit(0)
            os.unlink("deps.dot")
            logging.info("Graph generated")

        else:
            logging.warning(f"No graph as no var linked to {lvar}")
