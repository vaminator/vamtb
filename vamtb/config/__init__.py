from pathlib import Path
import yaml

from vamtb.vamex import *
from vamtb.utils import *
from vamtb.log import *

class ConfigMgr:
    global C_YAML
    __streamname = None
    __conf = None

    def __init__(self, config_file = C_YAML):
        """
        """

        ConfigMgr.__streamname = config_file
        try:
            stream = open(ConfigMgr.__streamname, 'r')
        except FileNotFoundError:
            stream = open(ConfigMgr.__streamname, 'w')
            print(red(f"Created {ConfigMgr.__streamname}"))
        finally:
            stream.close()

    def read_conf(self):
        """
        Read whole configuration
        """
        with open(ConfigMgr.__streamname, 'r') as stream:
            conf = yaml.load(stream, Loader=yaml.BaseLoader)
            ConfigMgr.__conf = conf if conf else {}
            debug(f"Loaded conf {ConfigMgr.__streamname}: {ConfigMgr.__conf}")

    def get(self, key_name, ask=None):
        """
        Read a key_name and if it doesn't exist, ask value and write it down. Unless ask is False
        """
        self.read_conf()
        if ConfigMgr.__conf and key_name in ConfigMgr.__conf:
            return ConfigMgr.__conf[key_name]
        if ask:
            value = input(ask + ":")
            self.set(key_name, value)
            return value
        else:
            return None

    def set(self, key_name, value):
        """
        Write value to configuration
        """
        self.read_conf()
        ConfigMgr.__conf[key_name] = value
        with open(ConfigMgr.__streamname, 'w') as outfile:
            yaml.dump(ConfigMgr.__conf, outfile, default_flow_style=False)
            info(f"Stored option {key_name} in config file.")

    def delete(self, key_name):
        """
        Remove configuration item
        """
        self.read_conf()
        try:
            del ConfigMgr.__conf[key_name]
        except KeyError:
            pass
        else:
            with open(ConfigMgr.__streamname, 'w') as outfile:
                yaml.dump(ConfigMgr.__conf, outfile, default_flow_style=False)
                debug(f"Removed entry {key_name} from config file.")
