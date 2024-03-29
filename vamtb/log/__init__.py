import colorama
import logging
import sys

class __Color:
    
    def __init__(self):
        logging.debug("Color class initialized")
    
    @staticmethod
    def col_clear():
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

    @dec_cl
    def yellowf(self, msg):
        return colorama.Fore.YELLOW + msg

    @dec_cl
    def lbluef(self, msg):
        return colorama.Fore.LIGHTBLUE_EX + msg

def green(message):
    return __col.greenf(message)

def red(message):
    return __col.redf(message)

def yellow(message):
    return __col.yellowf(message)

def blue(message):
    return __col.lbluef(message)

class CustomFormatter(logging.Formatter):

    blue        = colorama.Fore.BLUE
    yellow      = colorama.Fore.YELLOW
    cyan        = colorama.Fore.CYAN
    green       = colorama.Fore.GREEN
    red         = colorama.Fore.LIGHTRED_EX
    bold_red    = colorama.Fore.RED
    reset       = colorama.Style.RESET_ALL

    #format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s (%(filename)s:%(lineno)d)"
    format = "%(levelname)8s : %(message)s"

    FORMATS = {
         logging.DEBUG: blue + format + reset,
         logging.INFO: green + format + reset,
         logging.WARNING: cyan + format + reset,
         logging.ERROR: red + format + reset,
         logging.CRITICAL: bold_red + format + reset
     }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)

class Log():
   
    __instance = None

    def __init__(self):
        if not Log.__instance:
            self.__ch = None
            self.__fh = None
            self.__logger = self.init_logging()
            Log.__instance = self

    def init_logging(self):

        logger = logging.getLogger("vamtb")
        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        self.__fh = logging.FileHandler("log-vamtb.txt", mode="w")
        self.__fh.setFormatter(formatter)
        self.__fh.setLevel(logging.DEBUG)
        logger.addHandler(self.__fh)

        self.__ch = logging.StreamHandler()
        self.__ch.setFormatter(CustomFormatter())
        self.__ch.setLevel(logging.WARNING)
        logger.addHandler(self.__ch)

        logger.propagate = False

        return logger

    @staticmethod
    def toLevel(level):
        levels = {
            "WARNING": logging.WARNING,
            "INFO": logging.INFO,
            "DEBUG": logging.DEBUG
        }
        if level in levels.values():
            pass
        elif level in levels:
            level = levels[level]
        elif 0 <= level <= 2:
            level = levels[{0: "WARNING", 1: "INFO", 2: "DEBUG"}[level]]
        else:
            print(f"Can set log level to {level}")
            sys.exit(0)
        return level

    def setLevel(self,level):
        self.__ch.setLevel(self.toLevel(level))

    def critical(self, message):
        self.__logger.critical(message)

    def error(self, message):
        self.__logger.error(message)

    def warn(self, message):
        self.__logger.warn(message)

    def info(self, message):
        self.__logger.info(message)

    def debug(self, message):
        self.__logger.debug(message)

def log_setlevel(level):
    __log.setLevel(level)

def info(message):
    __log.info(message)

def error(message):
    __log.error(message)

def warn(message):
    __log.warn(message)

def warning(message):
    __log.warn(message)

def critical(message, doexit=True):
    __log.critical(message)
    if doexit:
        sys.exit(0)

def debug(message):
     __log.debug(message)

# Singleton as Global variables
__col = __Color()
__log = Log()
