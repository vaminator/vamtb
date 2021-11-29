import subprocess
import os
#from vamtb.varfile import Var
from vamtb.utils import *
from vamtb.log import *

class Graph:
    __instance = None

    def __init__(self):
        if not Graph.__instance:
            Graph.__instance = self
    
    @staticmethod
    def set_props(var_list, dir)->str:
        res = []
        for var in var_list:
            res.append(f'"{var}" [color={"blue" if Var(var, dir=dir, use_db=True).exists else "red"}];')
            license = Var(var).license
            if license in ("PC", "Questionable"):
                res.append(f'"{var}" [shape=box];')
        return res

    @staticmethod
    def set_size(tree):
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

    @staticmethod
    def dotty(lvar=None):

        direct_graphs=[]

        #if isinstance(lvar, os.PathLike):
        #    lvar = VarFile(lvar).var

        tree = Graph.treedown(lvar)
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

        dot_lines = Graph.set_props(all_vars)
        # Calculate real size of top var
        tree[lvar]['totsize'] = tree[lvar]['size']
        for v in all_vars:
            if v in tree and v != lvar:
                tree[lvar]['totsize'] += tree[v]['size']
        labels = Graph.set_size(tree)
        
        dot_lines.extend(list(set(direct_graphs)))
        dot_lines.extend(labels)

        with open("deps.dot", "w") as f:
            f.write("digraph vardeps {" + "\n" +
            "\n".join(dot_lines) + "\n" +
            "}")

        pdfname = f"{C_DDIR}\{lvar}.pdf" if lvar else f"{C_DDIR}\deps.pdf"
        if not os.path.exists(C_DDIR):
            os.makedirs(C_DDIR)
        try:
            subprocess.run(f'{C_DOT} -Gcharset=latin1 -Tpdf -o "{pdfname}" deps.dot', check=True, capture_output=True, encoding="utf-8")
        except subprocess.CalledProcessError as e:
            error(f"Graphiz returned: {e.stderr.rstrip()}")
            error([line.strip() for line in open("deps.dot")])
            os.unlink("deps.dot")
            exit(0)
        os.unlink("deps.dot")
        info("Graph generated")

# Singleton as Global variable 
__graph = Graph()
