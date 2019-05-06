from .exceptions import InvalidContentID


def int_id(prefix, content_id):
    if isinstance(content_id, int):
        return content_id
    elif isinstance(content_id, str):
        try:
            if prefix and content_id.startswith(prefix):
                return int(content_id[len(prefix):])
            return int(content_id)
        except ValueError:
            pass
    raise InvalidContentID('invalid context id: {}'.format(content_id))


def str_id(prefix, content_id):
    return prefix + str(int_id(prefix, content_id))
