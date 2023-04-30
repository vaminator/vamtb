import json
from json import decoder
from pathlib import Path
import os
import json
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
            content = self.read()
            try:
                # Normalize json content
                json_content = json.loads(content)
            except (UnicodeDecodeError, json.decoder.JSONDecodeError):
                #Was not json or not UTF-8 json
                pass
            else:
                #TODO check for vaj: displayName (, creatorName)
                if self.path.suffix == ".vmi":
                    json_content.pop('group')
                    json_content.pop('region')
                content = json.dumps(json_content).encode('utf8')
            self.__crc = crc32c(content)
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

    def read(self):
        return open(self.__fname,'rb').read()

    def open(self):
        return open(self.__fname)

    @property
    def jsonDeps(self, fuzzy=False):
        """
        Get  dependency from inspecting json
        FIXME "MeshedVR.PresetsPack.latest:MeshedVR/PresetsPack/Ren_Tina" is also correct
        FIXME "UserLUT" : "Oeshii.Hani.1:/Custom/Assets/MacGruber/PostMagic/LUT32/PhotoStudio_LUT02.png" as parameter of plugin#1_MacGruber.PostMagic.UserLUT 
        """
        deps = { 'embed': [], 'var': [] , 'self': [] }
        def _decode_dict(a_dict):
            for id, ref in a_dict.items():  # pylint: disable=unused-variable
                if not fuzzy and not id_is_ref(id):
                    continue
                if type(ref) == str:
                    if ref.startswith("SELF:/"):
                        # Link to self (embedded)
                        deps['self'].append(ref)
                    elif ":/" in ref[1:]:
                        # Link to Other
                        name = ref.split(':')
                        if len(name) == 2:
                            name = name[0]
                            ndot = len(name.split('.'))
                            if ndot == 3:
                                deps['var'].append(ref)
                    elif any(ref.endswith(s) for s in ['.vmi', ".vam", ".vap",".json"]):
                        # Local to file (embedded) without SELF
                        deps['embed'].append(ref)

        _ = json.loads(self.read(), object_hook=_decode_dict)
        # debug(f"Decoded json from {self.name()}, deps={deps}")
        return deps