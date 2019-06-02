class NiconicoException(Exception):
    def __init__(self, *args, **kwargs):
        if len(args) == 1:
            args = ('niconico: {}'.format(args[0]),)
        elif len(args) > 1:
            args = ('niconico: {}'.format(args),)
        super().__init__(*args, **kwargs)


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
