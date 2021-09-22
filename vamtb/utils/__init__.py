#from colorama import Fore, Back, Style, init
from vamtb import vamex
import colorama
import os


# Types
T_UNK= 0
T_SCENE = 1<<1
T_PERSON = 1<<2
T_HAIR = 1<<3
T_CLOTH = 1<<4
T_POSE = 1<<5
T_MORPH = 1<<6

T_HAIRP = 1<<7
T_CLOTHP = 1<<8
T_POSEP = 1<<9
T_MORPHP = 1<<10

T_ASSET = 1<<11
T_SCRIPT = 1<<12

T_VAC = 1<<13

T_MALE = 1<<14
T_FEMALE = 1<<15

T_JPG = 1<<16

T_VAP = 1<<17  # for now, any preset is a VAP

T_DIR = 1<<18

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