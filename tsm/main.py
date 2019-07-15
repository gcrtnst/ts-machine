import contextlib
import json
import sys
from argparse import ArgumentParser
from http.cookiejar import LWPCookieJar
from json import JSONDecodeError
from pathlib import Path

import toml
from cerberus import Validator
from toml import TomlDecodeError

from .tsm import TSMachine

config_schema = {
    'login': {
        'type': 'dict',
        'required': True,
        'schema': {
            'mail': {'type': 'string', 'required': True},
            'password': {'type': 'string', 'required': True},
            'cookieJar': {'type': 'string'},
        },
    },
    'search': {
        'type': 'list',
        'default': [],
        'schema': {
            'type': 'dict',
            'schema': {
                'q': {'type': 'string', 'required': True},
                'targets': {'type': 'list', 'valuesrules': {'type': 'string'},
                            'default': ['title', 'description', 'tags']},
                'sort': {'type': 'string', 'default': '+startTime'},
                'jsonFilter': {'type': 'string'},
                'openTimeFrom': {'type': 'string'},
                'openTimeTo': {'type': 'string'},
                'startTimeFrom': {'type': 'string'},
                'startTimeTo': {'type': 'string'},
                'liveEndTimeFrom': {'type': 'string'},
                'liveEndTimeTo': {'type': 'string'},
                'ppv': {'type': 'boolean'},
            },
        },
    },
    'warn': {
        'type': 'dict',
        'default': {},
        'schema': {
            'tsNotSupported': {'type': 'boolean', 'default': True},
            'tsRegistrationExpired': {'type': 'boolean', 'default': True},
            'tsMaxReservation': {'type': 'boolean', 'default': True},
        },
    },
    'misc': {
        'type': 'dict',
        'default': {},
        'schema': {
            'overwrite': {'type': 'boolean', 'default': False},
            'timeout': {'type': 'number'},
            'userAgent': {'type': 'string'},
            'context': {'type': 'string'},
        },
    },
}


class ConfigError(Exception):
    pass


def load_config(path):
    path = Path(path)
    try:
        with path.open() as f:
            config = toml.load(f)
    except TomlDecodeError as e:
        raise ConfigError('config: toml: {}'.format(e))

    v = Validator(config_schema)
    if not v.validate(config):
        raise ConfigError('config: {}'.format(v.errors))
    config = v.document

    basepath = path.parent
    if 'cookieJar' in config['login']:
        config['login']['cookieJar'] = Path(
            basepath, config['login']['cookieJar'])
    for search in config['search']:
        if 'jsonFilter' in search:
            search['jsonFilter'] = Path(basepath, search['jsonFilter'])
    return config


@contextlib.contextmanager
def lwp_cookiejar(filename=None, filemode=0o666):
    if filename is not None:
        filename = Path(filename)

    jar = LWPCookieJar()
    if filename is not None and filename.exists():
        jar.load(str(filename))
    try:
        yield jar
    finally:
        if filename is None:
            return
        filename.touch(mode=filemode)
        jar.save(str(filename))


def main():
    argp = ArgumentParser()
    argp.add_argument(
        '-c', '--config', type=Path,
        default=Path('~', '.config', 'tsm', 'config.toml').expanduser(),
        help='TOML-formatted configuration file (default: %(default)s)')
    argp.add_argument(
        '-s', '--search', type=int, nargs='?', const=10, metavar='N',
        help=('search only mode; \n'
              'N specifies maximum number of programs to search \n'
              '(default: %(const)s)'))
    argv = argp.parse_args()

    try:
        config = load_config(argv.config)
    except OSError as e:
        sys.exit("error: config '{}': {}".format(argv.config, e.strerror))
    except ConfigError as e:
        sys.exit('error: ' + str(e))

    filter_list = config['search'].copy()
    for i in range(len(filter_list)):
        if 'jsonFilter' not in config['search'][i]:
            continue
        try:
            with Path(config['search'][i]['jsonFilter']).open() as f:
                filter_list[i]['jsonFilter'] = json.load(f)
        except OSError as e:
            sys.exit("error: jsonFilter '{}': {}".format(
                config['search'][i]['jsonFilter'], e.strerror))
        except JSONDecodeError as e:
            sys.exit("error: jsonFilter: {}".format(e))

    with lwp_cookiejar(filename=config['login'].get('cookieJar'),
                       filemode=0o600) as jar, TSMachine() as tsm:
        tsm.mail = config['login']['mail']
        tsm.password = config['login']['password']
        tsm.cookies = jar
        tsm.timeout = config['misc'].get('timeout')
        tsm.user_agent = config['misc'].get('userAgent')
        tsm.context = config['misc'].get('context')
        tsm.filter_list = filter_list
        tsm.overwrite = config['misc']['overwrite']
        tsm.warnings = set()
        if config['warn']['tsNotSupported']:
            tsm.warnings.add('ts_not_supported')
        if config['warn']['tsRegistrationExpired']:
            tsm.warnings.add('ts_registration_expired')
        if config['warn']['tsMaxReservation']:
            tsm.warnings.add('ts_max_reservation')
        if argv.search is not None:
            sys.exit(tsm.run_search_only(argv.search))
        sys.exit(tsm.run_auto_reserve())


if __name__ == '__main__':
    main()
