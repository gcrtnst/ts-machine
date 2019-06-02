class NiconicoException(Exception):
    pass


class CommunicationError(NiconicoException):
    pass


class Timeout(CommunicationError):
    pass


class InvalidResponse(NiconicoException):
    pass


class InvalidContentID(NiconicoException, ValueError):
    pass


class LoginFailed(NiconicoException):
    pass


class LoginRequired(NiconicoException):
    pass


class NotFound(NiconicoException):
    pass


class TSNotSupported(NiconicoException):
    pass


class TSAlreadyRegistered(NiconicoException):
    pass


class TSRegistrationExpired(NiconicoException):
    pass


class TSReachedLimit(NiconicoException):
    pass


class ContentSearchError(NiconicoException):
    def __init__(self, *args, **kwargs):
        self.meta = kwargs.pop('meta', None)
        super().__init__(*args, **kwargs)
