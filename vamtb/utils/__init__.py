#from colorama import Fore, Back, Style, init
from vamtb import vamex
import colorama
import os

def getdir(ctx):
    mdir = ctx.obj['dir']
    if not mdir: 
        mdir = os.getcwd()
    if not mdir.endswith("AddonPackages"):
        mdir = f"{mdir}\\AddonPackages"
    if not os.path.isdir(mdir):
        raise vamex.BaseDirNotFound()
    return mdir

class Color:
    __instance = None
    
    @staticmethod 
    def getInstance():
        """ Static access method. """
        if Color.__instance == None:
            Color()
        return Color.__instance
    def __init__(self):
        """ Virtually private constructor. """
        if Color.__instance != None:
            raise Exception("This class is a singleton!")
        else:
            Color.__instance = self
    
    def col_clear(self):
        return colorama.Style.RESET_ALL

    def dec_cl(func):
        def inner(self, msg):
            return func(self, msg) + self.col_clear()
        return inner

    @dec_cl
    def redf(self, msg):
        return colorama.Fore.RED + msg

    @dec_cl
    def greenf(self, msg):
        return colorama.Fore.GREEN + msg

ucol = Color()