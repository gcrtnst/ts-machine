import contextlib
import itertools
import re
import sys
from argparse import ArgumentParser
from datetime import timedelta
from http.cookiejar import LWPCookieJar
from pathlib import Path

import dateutil.tz
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
    def __init__(self):
        self._niconico = Niconico()
        self._niconico.tz = dateutil.tz.gettz()

        self.filters = {}
        self.overwrite = False
        self.stdout = sys.stdout
        self.stderr = sys.stderr

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

    @property
    def user_agent(self):
        return self._niconico.user_agent

    @user_agent.setter
    def user_agent(self, value):
        self._niconico.user_agent = value

    @property
    def context(self):
        return self._niconico.context

    @context.setter
    def context(self, value):
        self._niconico.context = value

    @property
    def tz(self):
        return self._niconico.tz

    @tz.setter
    def tz(self, value):
        self._niconico.tz = value

    def ts_register(self, live_id):
        self._niconico.ts_register(live_id, overwrite=self.overwrite)

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

    def iter_search(self, fields=set()):
        search_fields = {'contentId', 'channelId'} | set(fields)
        iter_contents = self._niconico.contents_search(
            self.filters['q'],
            service='live',
            targets=self.filters['targets'],
            fields=search_fields,
            filters=self.contents_search_filters(),
            sort=self.filters['sort'],
        )

        for content in iter_contents:
            if 'ppv' in self.filters:
                is_ppv = content['channelId'] is not None and self._niconico.is_ppv_live(content['contentId'], content['channelId'])
                if is_ppv != self.filters['ppv']:
                    continue
            yield {k: v for k, v in content.items() if k in fields}

    def print(self, *args, **kwargs):
        kwargs['file'] = kwargs.get('file', self.stdout)
        print(*args, **kwargs)

    def print_err(self, *args, **kwargs):
        kwargs['file'] = kwargs.get('file', self.stderr)
        print(*args, **kwargs)

    def print_diff(self, ts_list_before, ts_list_after):
        for ts in ts_list_after:
            if ts['vid'] in (ts['vid'] for ts in ts_list_before):
                continue
            self.print('added:   ' + ts['vid'] + ': ' + ts['title'])

        for ts in ts_list_before:
            if ts['vid'] in (ts['vid'] for ts in ts_list_after):
                continue
            self.print('removed: ' + ts['vid'] + ': ' + ts['title'])

    def run_search_only(self, n):
        iter_search = self.iter_search(fields={'contentId', 'title'})
        iter_search = itertools.islice(iter_search, n)
        for content in iter_search:
            self.print(content['contentId'] + ': ' + content['title'])

    def run_auto_reserve(self):
        ts_list_before = self._niconico.ts_list()
        for content in self.iter_search(fields={'contentId'}):
            if content['contentId'] in (ts['vid'] for ts in ts_list_before):
                continue
            try:
                self.ts_register(content['contentId'])
            except TSAlreadyRegistered:
                continue
            except TSRegistrationExpired:
                self.print_err('warning: timeshift registration expired for ' + content['contentId'])
                continue
            except TSReachedLimit:
                self.print_err('warning: reached limit')
                break

        ts_list_after = self._niconico.ts_list()
        self.print_diff(ts_list_before, ts_list_after)


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
    argp.add_argument('-c', '--config', type=Path, default=Path('~', '.tsm').expanduser(), help='TOML-formatted configuration file (default: %(default)s)')
    argp.add_argument('-s', '--search', type=int, nargs='?', const=10, metavar='N', help='search only mode; N specifies maximum number of programs to search (default: %(const)s)')
    argv = argp.parse_args()

    with argv.config.open() as f:
        config = toml.load(f)
    config['search']['targets'] = config['search'].get('targets', ['title', 'description', 'tags'])
    config['search']['sort'] = config['search'].get('sort', '+startTime')
    config['search']['startAfter'] = config['search'].get('startAfter', '30m')
    config['misc'] = config.get('misc', {})
    config['misc']['overwrite'] = config['misc'].get('overwrite', False)
    config['misc']['timeout'] = config['misc'].get('timeout', 300)
    config['misc']['userAgent'] = config['misc'].get('userAgent', requests.utils.default_user_agent() + ' ts-machine (private app)')
    config['misc']['context'] = config['misc'].get('context', config['misc']['userAgent'])

    with lwp_cookiejar(filename=config['login'].get('cookieJar')) as jar:
        tsm = TSMachine()
        tsm.mail = config['login']['mail']
        tsm.password = config['login']['password']
        tsm.cookies = jar
        tsm.timeout = config['misc']['timeout']
        tsm.user_agent = config['misc']['userAgent']
        tsm.context = config['misc']['context']
        tsm.filters = config['search']
        tsm.overwrite = config['misc']['overwrite']
        if argv.search is not None:
            tsm.run_search_only(argv.search)
        else:
            tsm.run_auto_reserve()


if __name__ == '__main__':
    main()
