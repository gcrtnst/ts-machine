import re
from argparse import ArgumentParser
from contextlib import contextmanager
from datetime import timedelta
from http.cookiejar import LWPCookieJar
from itertools import chain
from pathlib import Path
from sys import stdout

import requests.utils
import toml

from niconico import (Niconico, TSAlreadyRegistered, TSReachedLimit,
                      TSRegistrationExpired)


def parse_timedelta(s):
    match = re.search(r'^((?P<weeks>\d+)w)?((?P<days>\d+)d)?((?P<hours>\d+)h)?((?P<minutes>\d+)m)?((?P<seconds>\d+)s)?((?P<milliseconds>\d+)ms)?((?P<microseconds>\d+)us)?$', s)
    if not match:
        raise ValueError('invalid timedelta: "{}"'.format(s))
    kwargs = {name: int(value) for (name, value) in match.groupdict().items() if value is not None}
    return timedelta(**kwargs)


class TSMachine:
    def __init__(self, mail, password, filters, cookies=None, simulate=False, stdout=stdout):
        self.filters = filters
        self.simulate = simulate
        self.stdout = stdout

        self._niconico = Niconico()
        self._niconico.mail = mail
        self._niconico.password = password
        self._niconico.user_agent = requests.utils.default_user_agent() + ' ts-machine (private app)'
        self._niconico.context = self._niconico.user_agent
        if cookies is not None:
            self._niconico.cookies = cookies

        self._ts_detail_list = None

    @property
    def ts_detail_list(self):
        if self._ts_detail_list is None:
            self._ts_detail_list = self._niconico.ts_detail_list()
        return self._ts_detail_list

    @ts_detail_list.setter
    def ts_detail_list(self, value):
        self._ts_detail_list = value

    def contents_search_filters(self, now=None):
        if now is None:
            now = self._niconico.server_time()

        filters = {
            'timeshiftEnabled': True,
            'liveStatus': 'reserved',
        }
        for key in ['userId', 'channelId', 'communityId', 'providerType', 'tags', 'memberOnly']:
            if key in self.filters:
                filters[key] = self.filters[key]
        for key, field, comp in [
                ('openBefore', 'openTime', 'lte'),
                ('openAfter', 'openTime', 'gte'),
                ('startBefore', 'startTime', 'lte'),
                ('startAfter', 'startTime', 'gte'),
        ]:
            if key not in self.filters:
                continue
            filters[field] = filters.get(field, {})
            filters[field][comp] = now + parse_timedelta(self.filters[key])
        if 'scoreTimeshiftReserved' in self.filters:
            filters['scoreTimeshiftReserved'] = {'gte': self.filters['scoreTimeshiftReserved']}
        return filters

    def iter_unreserved(self, fields={'contentId'}):
        search_fields = {'contentId', 'title', 'channelId'} | set(fields)
        iter_search = self._niconico.contents_search(
            self.filters['q'],
            service='live',
            targets=self.filters['targets'],
            fields=search_fields,
            filters=self.contents_search_filters(),
            sort=self.filters['sort'],
        ).__iter__()

        try:
            content = iter_search.__next__()
        except StopIteration:
            return
        iter_search = chain([content], iter_search)

        for content in iter_search:
            if content['contentId'] in (ts['vid'] for ts in self.ts_detail_list):
                continue
            if 'ppv' in self.filters:
                is_ppv = content['channelId'] is not None and self._niconico.is_ppv_live(content['contentId'], content['channelId'])
                if is_ppv != self.filters['ppv']:
                    continue
            yield {k: v for k, v in content.items() if k in fields}

    def run(self):
        for content in self.iter_unreserved(fields={'contentId', 'title'}):
            try:
                if not self.simulate:
                    self._niconico.ts_register(content['contentId'])
            except TSReachedLimit:
                return
            except (TSAlreadyRegistered, TSRegistrationExpired):
                continue
            print('reserved: ' + content['contentId'] + ': ' + content['title'], file=self.stdout)
            self.ts_detail_list.append({
                'vid': content['contentId'],
                'title': content['title'],
                'status': 'RESERVED',
                'unwatch': False,
                'expire': None,
            })


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


def main():
    argp = ArgumentParser()
    argp.add_argument('config', type=Path, help='TOML-formatted configuration file')
    argp.add_argument('-s', '--simulate', action='store_true', help='simulate timeshift reservation')
    argv = argp.parse_args()

    with argv.config.open() as f:
        config = toml.load(f)
    config['search']['targets'] = config['search'].get('targets', ['title', 'description', 'tags'])
    config['search']['sort'] = config['search'].get('sort', '+startTime')
    config['search']['startAfter'] = config['search'].get('startAfter', '30m')

    with lwp_cookiejar(filename=config['login'].get('cookieJar')) as jar:
        TSMachine(config['login']['mail'], config['login']['password'], config['search'], cookies=jar, simulate=argv.simulate).run()


if __name__ == '__main__':
    main()
