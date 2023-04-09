from pathlib import Path
import yaml

from vamtb.vamex import *
from vamtb.utils import *
from vamtb.log import *

class ConfigMgr:
    global C_YAML

    def __init__(self, config_file = C_YAML):
        """
        """
        self.__streamname = config_file
        self.__conf = None

        try:
            self.__stream = open(config_file, 'r')
        except FileNotFoundError:
            self.__stream = open(config_file, 'w')
            info(f"Created {config_file}")
        self.__stream.close()

    def read_conf(self):
        """
        Read whole configuration
        """
        with open(self.__streamname, 'r') as stream:
            self.__conf = yaml.load(stream, Loader=yaml.BaseLoader)

    def get(self, key_name, ask=None):
        """
        Read a key_name and if it doesn't exist, ask value and write it down. Unless ask is False
        """
        self.read_conf()
        if key_name in self.__conf:
            return self.__conf[key_name]
        if not ask:
            return None
        value = input(ask + ":")
        self.set(key_name, value)

    def set(self, key_name, value):
        """
        Write value to configuration
        """
        self.read_conf()
        self.__conf[key_name] = value
        with open(C_YAML, 'w') as outfile:
            yaml.dump(self.__conf, outfile, default_flow_style=False)
            info(f"Stored option {key_name} in config file.")
