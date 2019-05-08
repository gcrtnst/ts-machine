import contextlib
import itertools
import re
import sys
from argparse import ArgumentParser
from datetime import timedelta
from http.cookiejar import LWPCookieJar
from pathlib import Path

import requests.utils
import toml

from niconico import Niconico, TSAlreadyRegistered, TSRegistrationExpired


def parse_timedelta(s):
    match = re.search(r'^((?P<weeks>\d+)w)?((?P<days>\d+)d)?((?P<hours>\d+)h)?((?P<minutes>\d+)m)?((?P<seconds>\d+)s)?((?P<milliseconds>\d+)ms)?((?P<microseconds>\d+)us)?$', s)
    if not match:
        raise ValueError('invalid timedelta: "{}"'.format(s))
    kwargs = {name: int(value) for (name, value) in match.groupdict().items() if value is not None}
    return timedelta(**kwargs)


class TSMachine:
    def __init__(self):
        self._niconico = Niconico()
        self._niconico.user_agent = requests.utils.default_user_agent() + ' ts-machine (private app)'
        self._niconico.context = self._niconico.user_agent

        self.filters = {}
        self.limit = None
        self.simulate = False
        self.stdout = sys.stdout
        self._ts_list = None

    @property
    def mail(self):
        return self._niconico.mail

    @mail.setter
    def mail(self, value):
        self._niconico.mail = value

    @property
    def password(self):
        return self._niconico.password

    @password.setter
    def password(self, value):
        self._niconico.password = value

    @property
    def cookies(self):
        return self._niconico.cookies

    @cookies.setter
    def cookies(self, value):
        self._niconico.cookies = value

    @property
    def timeout(self):
        return self._niconico.timeout

    @timeout.setter
    def timeout(self, value):
        self._niconico.timeout = value

    def ts_list(self):
        if self._ts_list is None:
            self._ts_list = self._niconico.ts_list()
        return self._ts_list[:]

    def ts_register(self, live_id):
        if not self.simulate:
            self._niconico.ts_register(live_id)
        if self._ts_list is not None:
            self._ts_list.append(live_id)

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

    def iter_reserve(self, fields={'contentId'}):
        search_fields = {'contentId', 'title', 'channelId'} | set(fields)
        iter_search = self._niconico.contents_search(
            self.filters['q'],
            service='live',
            targets=self.filters['targets'],
            fields=search_fields,
            filters=self.contents_search_filters(),
            sort=self.filters['sort'],
        )

        for content in iter_search:
            if content['contentId'] in self.ts_list():
                continue
            if 'ppv' in self.filters:
                is_ppv = content['channelId'] is not None and self._niconico.is_ppv_live(content['contentId'], content['channelId'])
                if is_ppv != self.filters['ppv']:
                    continue
            yield {k: v for k, v in content.items() if k in fields}

    def run(self):
        iter_reserve = self.iter_reserve(fields={'contentId', 'title'})
        if self.limit is not None:
            iter_reserve = itertools.takewhile(lambda _: len(self.ts_list()) < self.limit, iter_reserve)

        for content in iter_reserve:
            try:
                self.ts_register(content['contentId'])
            except (TSAlreadyRegistered, TSRegistrationExpired):
                continue
            print('reserved: ' + content['contentId'] + ': ' + content['title'], file=self.stdout)


@contextlib.contextmanager
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
    config['misc'] = config.get('misc', {})
    config['misc']['timeout'] = config['misc'].get('timeout', 300)
    config['misc']['timeshiftLimit'] = config['misc'].get('timeshiftLimit', 10)

    with lwp_cookiejar(filename=config['login'].get('cookieJar')) as jar:
        tsm = TSMachine()
        tsm.mail = config['login']['mail']
        tsm.password = config['login']['password']
        tsm.cookies = jar
        tsm.timeout = config['misc']['timeout']
        tsm.limit = config['misc']['timeshiftLimit']
        tsm.filters = config['search']
        tsm.simulate = argv.simulate
        tsm.run()


if __name__ == '__main__':
    main()
