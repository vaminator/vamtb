class OneParamException(Exception):
    """Exception having one parameter whose message is that parameter
       Exception description can be set and returned on will
    """
    def __init__(self, param, exceptionDesc):
        self.message = param

    def __str__(self):
        return f'{self.message}'
    

class VarNotFound(OneParamException):
    """Exception raised for not present VAR.

    """

    def __init__(self, varname):
        super().__init__(varname, "VarNotFound")


class VarNameNotCorrect(Exception):
    """Exception raised for incorrectly named VAR.

    """

    def __init__(self, varname):
        super().__init__(varname, "VarNameNotCorrect")


class VarExtNotCorrect(Exception):
    """Exception raised for VAR with wrong extension.

    """

    def __init__(self, varname):
        super().__init__(varname, "VarExtNotCorrect")


class VarVersionNotCorrect(Exception):
    """Exception raised for VAR with wrong version.

    """

    def __init__(self, varname):
        super().__init__(varname, "VarVersionNotCorrect")


class VarMetaJson(Exception):
    """Exception raised for bad json.

    """

    def __init__(self, varname):
        super().__init__(varname, "VarMetaJson")


class NoMetaJson(OneParamException):
    """Exception raised for not present meta.json.

    """

    def __init__(self, varname):
        super().__init__(varname, "MetaJsonNotFound")


class UnknownExtension(Exception):
    """Exception raised for unknown extension.

    """

    def __init__(self, varname):
        super().__init__(varname, "UnknownExtension")


class IllegalPath(Exception):
    """Exception raised for illegal path inside var

    """

    def __init__(self, varname):
        super().__init__(varname, "IllegalPath")


class MissingFiles(Exception):
    """Exception raised for missing associated file for content

    """

    def __init__(self, varname):
        super().__init__(varname, "MissingFiles")


class UnknownContent(Exception):
    """Exception raised for undetected content

    """

    def __init__(self, varname):
        super().__init__(varname, "UnknownContent")

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