import json
from vamtb import utils
from pathlib import Path
from vamtb.utils import *

class FileName:
    def __init__(self, fname, calc_crc = False) -> None:
        self.__fname = Path(fname)
        self.__crc = 0
        if calc_crc:
            self.__crc = self.crc

    def __repr__(self) -> str:
        return f"{self.__fname} [CRC {self.__crc}]"

    def __str__(self) -> str:
        return f"{self.__fname}"

    @property
    def path(self):
        return self.__fname
    
    @property
    def name(self):
        return self.__fname.name

    @property
    def crc(self):
        if not self.__crc:
            self.__crc = crc32c(self.read())
        return self.__crc

    @property
    def mtime(self):
        self.__mtime = os.path.getmtime(self.path)
        return self.__mtime

    @property
    def size(self):
        self.__size = os.path.getsize(self.path)
        return self.__size

    @property
    def json(self):
        return json.loads(self.read())

    @property
    def jsonDeps(self):
        deps = { 'embed': [], 'var': [] , 'self': [] }
        def _decode_dict(a_dict):
            for id, ref in a_dict.items():  # pylint: disable=unused-variable
                if type(ref) == str:
                    if ref.startswith("SELF:"):
                        # Link to self
                        deps['self'].append(ref)
                    elif ":" in ref[1:]:
                        # Link to Other
                        name = ref.split(':')[0]
                        ndot = len(name.split('.'))
                        if ndot == 3:
                            deps['var'].append(ref)
                    elif any(ref.endswith(s) for s in ['.vmi', ".vam", ".vap", ".json"]):
                        # String not containing ":" ending with these extensions
                        deps['embed'].append(ref)

        _ = json.loads(self.read(), object_hook=_decode_dict)
        # logging.debug(f"Decoded json from {self.name()}, deps={deps}")
        return deps

    def read(self):
        return open(self.__fname,'rb').read()

    def open(self):
        return open(self.__fname)
