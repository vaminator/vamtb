class OneParamException(BaseException):
    """Exception having one parameter whose message is that parameter
       Exception description can be set and returned on will
    """
    def __init__(self, param, exceptionDesc):
        self.message = param

    def __str__(self):
        return f'{self.message}'
    
class BaseDirNotFound(OneParamException):
    """Exception raised for non existent AddonPackages.

    """

    def __init__(self):
        super().__init__("", "BaseDirNotfound")

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

VarFileNameIncorrect = (VarExtNotCorrect, VarNameNotCorrect, VarVersionNotCorrect)

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
