import re

from .exceptions import InvalidContentID


def int_id(prefix, content_id):
    if isinstance(content_id, int):
        return content_id
    elif isinstance(content_id, str):
        match = re.search(r'^(?P<prefix>[a-z]+)?(?P<id>[0-9]+)$', content_id)
        if match:
            match_prefix = match.group('prefix')
            if match_prefix and match_prefix != prefix:
                raise InvalidContentID('expected "' + prefix + '" for content id prefix, found "' + match_prefix + '"')
            return int(match.group('id'))
    raise InvalidContentID('invalid context id: {}'.format(content_id))


def str_id(prefix, content_id):
    return prefix + str(int_id(prefix, content_id))
