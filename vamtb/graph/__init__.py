from vamtb import db
import subprocess
import os
from vamtb.utils import *
from vamtb.log import *
from vamtb.varfile import VarFile

class Graph:
    __desc_deps=[]
    __asc_deps=[]
    __dbs=None

    def __init__(self, dbs=None):
        if not dbs:
            dbs = db.Dbs()
        Graph.__dbs = dbs

    def set_props(self, var_list):
        res = []
        for var in var_list:
            res.append(f'"{var}" [color={"blue" if Graph.__dbs.var_exists(var) else "red"}];')
            license = Graph.__dbs.get_license(var)
            if license in ("PC", "Questionable"):
                res.append(f'"{var}" [shape=box];')
        return res

    def treedown(self, var):
        """
        Return down dependency graph
        If dependency is not found, the graph will record this missing var but will stop there
        Depth first
        Returns {"var_name": [Deps], "other_var": [Deps]}
        """
        td_vars = {}
        def rec(var):
            td_vars[var] = { 'dep':[], 'size':0, 'totsize':0 }
            td_vars[var]['size'] = Graph.__dbs.get_var_size(var)
            for dep in Graph.__dbs.get_dep(var):
                #Descend for that depend if it exists
                vers = dep.split('.')[2]
                rdep = ""
                if vers == "latest":
                    rdep = Graph.__dbs.latest(dep)
                    # If var found, we use that one
                    # otherwise we'll keep the .latest one as leaf
                    if rdep:
                        dep = rdep
                elif vers.startswith("min"):
                    rdep = Graph.__dbs.min(dep)
                    if rdep:
                        dep = rdep
                td_vars[var]['dep'].append(dep)
                if dep and Graph.__dbs.var_exists(dep):
                    if dep == var:
                        error(f"There is a recursion from {var} to itself, avoiding")
                        continue
                    td_vars[var]['totsize'] += Graph.__dbs.get_var_size(dep)
                    rec(dep)
        td_vars = {}
        rec(var)
        return td_vars

    def set_size(self, tree):
        res = []
        for var in tree:
            size = f"{int(tree[var]['size']/1024/1024)}MB"
            if size == "0MB":
                size = f"{int(tree[var]['size']/1024)}KB"
            totsize = int(tree[var]['totsize']/1024/1024)
            if size or totsize:
                amsg = f" {totsize}MB" if totsize else ""
                res.append(f'"{var}" [xlabel="{size}{amsg}"];')
        return res

    def dotty(self, lvar=None):

        direct_graphs=[]
        cmddot = "c:\\Graphviz\\bin\\dot.exe"

        if isinstance(lvar, os.PathLike):
            lvar = VarFile(lvar).var

        tree = self.treedown(lvar)
        if not len(tree[lvar]['dep']):
            info("No deps, no graph")
            return
        for var in tree:
            for dep in tree[var]['dep']:
                direct_graphs.append(f'"{var}" -> "{dep}";')

        all_vars=[]
        for var in tree:
            all_vars.append(var)
            all_vars.extend(tree[var]['dep'])
        all_vars = list(set(all_vars))

        dot_lines = self.set_props(all_vars)
        # Calculate real size of top var
        tree[lvar]['totsize'] = tree[lvar]['size']
        for v in all_vars:
            if v in tree and v != lvar:
                tree[lvar]['totsize'] += tree[v]['size']
        labels = self.set_size(tree)
        
        dot_lines.extend(list(set(direct_graphs)))
        dot_lines.extend(labels)

        try:
            with open("deps.dot", "w") as f:
                f.write("digraph vardeps {" + "\n" +
                "\n".join(dot_lines) + "\n" +
                "}")
        except UnicodeEncodeError:
            #FIXME
            return

        pdfname = f"{C_DDIR}\{lvar}.pdf" if lvar else f"{C_DDIR}\deps.pdf"
        if not os.path.exists(C_DDIR):
            os.makedirs(C_DDIR)
        try:
            subprocess.check_call(f'{cmddot} -Gcharset=latin1 -Tpdf -o "{pdfname}" deps.dot')
        except Exception as CalledProcessError:
            error(f"Graphiz Error. Make sure you have graphviz installed in {cmddot} and a correct dot file.")
            error([line.strip() for line in open("deps.dot")])
            os.unlink("deps.dot")
            exit(0)
        os.unlink("deps.dot")
        info("Graph generated")