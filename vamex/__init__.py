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
