import re
from argparse import ArgumentParser
from contextlib import contextmanager
from datetime import datetime, timedelta
from http.cookiejar import LWPCookieJar
from pathlib import Path

import requests.utils
import toml
from dateutil.tz import gettz

from niconico import (Niconico, TSAlreadyRegistered, TSReachedLimit,
                      TSRegistrationExpired)


@contextmanager
def lwp_cookiejar(*args, **kwargs):
    jar = LWPCookieJar(*args, **kwargs)
    if jar.filename is not None and Path(jar.filename).is_file():
        jar.load()
    try:
        yield jar
    finally:
        if jar.filename is not None:
            jar.save()


def parse_timedelta(s):
    match = re.search(r'^((?P<weeks>\d+)w)?((?P<days>\d+)d)?((?P<hours>\d+)h)?((?P<minutes>\d+)m)?((?P<seconds>\d+)s)?((?P<milliseconds>\d+)ms)?((?P<microseconds>\d+)us)?$', s)
    if not match:
        raise ValueError('invalid timedelta: "{}"'.format(s))
    kwargs = {name: int(value) for (name, value) in match.groupdict().items() if value is not None}
    return timedelta(**kwargs)


def main():
    argp = ArgumentParser()
    argp.add_argument('config', type=Path, help='TOML-formatted configuration file')
    argp.add_argument('-s', '--simulate', action='store_true', help='simulate timeshift reservation')
    argv = argp.parse_args()
    with argv.config.open() as f:
        config = toml.load(f)

    with lwp_cookiejar(filename=config['login'].get('cookiejar')) as jar:
        n = Niconico()
        n.user_agent = requests.utils.default_user_agent() + ' autots (private app)'
        n.context = n.user_agent
        n.cookies = jar

        # login
        n.mail = config['login']['mail']
        n.password = config['login']['password']
        n.ensure_login()

        # ts_list
        ts_list = n.ts_list()

        # filters
        filters = {
            'timeshiftEnabled': True,
            'liveStatus': 'reserved',
            'userId': config['filters'].get('userId', []),
            'channelId': config['filters'].get('channelId', []),
            'communityId': config['filters'].get('communityId', []),
            'providerType': config['filters'].get('providerType', []),
            'tags': [t.replace(' ', '_') for t in config['filters'].get('tags', [])],
            'tagsExact': [t.replace(' ', '_') for t in config['filters'].get('tagsExact', [])],
        }

        now = datetime.now(tz=gettz())
        filters['openTime'] = {}
        filters['startTime'] = {}
        if 'openBefore' in config['filters']:
            filters['openTime']['lte'] = now + parse_timedelta(config['filters']['openBefore'])
        if 'openAfter' in config['filters']:
            filters['openTime']['gte'] = now + parse_timedelta(config['filters']['openAfter'])
        if 'startBefore' in config['filters']:
            filters['startTime']['lte'] = now + parse_timedelta(config['filters']['startBefore'])
        if 'startAfter' in config['filters']:
            filters['startTime']['gte'] = now + parse_timedelta(config['filters']['startAfter'])
        else:
            filters['startTime']['gte'] = now + timedelta(minutes=30)

        if 'scoreTimeshiftReserved' in config['filters']:
            filters['scoreTimeshiftReserved'] = {'gte': config['filters']['scoreTimeshiftReserved']}
        if 'memberOnly' in config['filters']:
            filters['memberOnly'] = config['filters']['memberOnly']

        resp = n.contents_search(
            config['filters']['q'],
            service='live',
            targets=config['filters'].get('targets', ['title', 'description', 'tags']),
            fields=['contentId', 'title', 'channelId'],
            filters=filters,
            sort=config['filters'].get('sort', '+startTime'),
            limit=20,
        )
        for c in resp['data']:
            if c['contentId'] in ts_list:
                continue
            if 'ppv' in config['filters']:
                is_ppv = c['channelId'] is not None and n.is_ppv_live(c['contentId'], c['channelId'])
                if config['filters']['ppv'] != is_ppv:
                    continue
            try:
                if not argv.simulate:
                    n.ts_register(c['contentId'])
            except TSReachedLimit:
                return
            except (TSAlreadyRegistered, TSRegistrationExpired):
                continue
            ts_list.append(c['contentId'])
            print('reserved: {}: {}'.format(c['contentId'], c['title']))


if __name__ == '__main__':
    main()
