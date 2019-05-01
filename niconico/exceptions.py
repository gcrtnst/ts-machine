class NiconicoException(Exception):
    pass


class InvalidResponse(NiconicoException):
    pass


class InvalidContentID(NiconicoException, ValueError):
    pass


class LoginFailed(NiconicoException):
    pass


class LoginRequired(NiconicoException):
    pass


class TSNotSupported(NiconicoException):
    pass


class TSAlreadyRegistered(NiconicoException):
    pass


class TSRegistrationExpired(NiconicoException):
    pass


class TSReachedLimit(NiconicoException):
    pass


class VitaError(NiconicoException):
    def __init__(self, *args, **kwargs):
        self.code = kwargs.pop('code', None)
        super().__init__(*args, **kwargs)


class ContentSearchError(NiconicoException):
    def __init__(self, *args, **kwargs):
        self.code = kwargs.pop('code', None)
        super().__init__(*args, **kwargs)
