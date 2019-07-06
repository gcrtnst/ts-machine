import re

from .exceptions import InvalidContentID


def parse_id(content_id):
    if isinstance(content_id, int):
        return (None, content_id)
    elif isinstance(content_id, str):
        match = re.search(r'^(?P<prefix>[a-z]+)?(?P<id>[0-9]+)$', content_id)
        if match:
            groupdict = match.groupdict()
            return (groupdict['prefix'], int(groupdict['id']))
    raise InvalidContentID('invalid context id: {}'.format(content_id))


def int_id(prefix, content_id):
    p, i = parse_id(content_id)
    if p is not None and p != prefix:
        raise InvalidContentID(
            'expected "' + prefix + '" for content id prefix, '
            'found "' + p + '"')
    return i


def str_id(prefix, content_id):
    return prefix + str(int_id(prefix, content_id))
