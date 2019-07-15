import functools
import itertools
import re
import sys
from datetime import timedelta

import dateutil.tz

from niconico import (CommunicationError, ContentSearchError, LoginFailed,
                      Niconico, Timeout, TSAlreadyRegistered, TSMaxReservation,
                      TSNotSupported, TSRegistrationExpired)

_re_timedelta = re.compile(r'^(?P<minus>-?)((?P<weeks>[0-9]+)w)?'
                           r'((?P<days>[0-9]+)d)?((?P<hours>[0-9]+)h)?'
                           r'((?P<minutes>[0-9]+)m)?((?P<seconds>[0-9]+)s)?'
                           r'((?P<milliseconds>[0-9]+)ms)?'
                           r'((?P<microseconds>[0-9]+)us)?$')


def parse_timedelta(s):
    match = _re_timedelta.search(s)
    if not match:
        raise ValueError('invalid timedelta: "{}"'.format(s))

    kwargs = {}
    for key in ['weeks', 'days', 'hours', 'minutes',
                'seconds', 'milliseconds', 'microseconds']:
        value = match.group(key)
        if value is not None:
            kwargs[key] = int(value)
    if match.group('minus'):
        return -timedelta(**kwargs)
    return timedelta(**kwargs)


def _tsm_run(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except ContentSearchError as e:
            if e.meta['status'] == 400:
                raise
            self.print_err('error: {}'.format(e))
        except (CommunicationError, LoginFailed, Timeout) as e:
            self.print_err('error: {}'.format(e))
        return 1
    return wrapper


class TSMachine:
    def __init__(self):
        self._niconico = Niconico()
        self._niconico.tz = dateutil.tz.gettz()

        self.filter_list = {}
        self.overwrite = False
        self.warnings = {
            'ts_not_supported', 'ts_max_reservation', 'ts_registration_expired'
        }
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

    def close_connection(self):
        return self._niconico.close_connection()

    def __enter__(self):
        self._niconico.__enter__()
        return self

    def __exit__(self, *args):
        return self._niconico.__exit__(*args)

    def ts_register(self, live_id):
        self._niconico.ts_register(live_id, overwrite=self.overwrite)

    def contents_search_json_filter(self, vfilter, now=None):
        json_filters = []
        if 'jsonFilter' in vfilter:
            json_filters.append(vfilter['jsonFilter'])
        for field, timefrom, timeto in [
            ('openTime', 'openTimeFrom', 'openTimeTo'),
            ('startTime', 'startTimeFrom', 'startTimeTo'),
            ('liveEndTime', 'liveEndTimeFrom', 'liveEndTimeTo'),
        ]:
            if timefrom not in vfilter and timeto not in vfilter:
                continue
            if now is None:
                now = self._niconico.server_time()

            jf = {'type': 'range', 'field': field}
            if timefrom in vfilter:
                dt = now + parse_timedelta(vfilter[timefrom])
                jf['from'] = dt.isoformat(timespec='seconds')
                jf['include_lower'] = True
            if timeto in vfilter:
                dt = now + parse_timedelta(vfilter[timeto])
                jf['to'] = dt.isoformat(timespec='seconds')
                jf['include_upper'] = True
            json_filters.append(jf)

        if len(json_filters) == 0:
            return None
        if len(json_filters) == 1:
            return json_filters[0]
        return {'type': 'and', 'filters': json_filters}

    def match_ppv(self, vfilter, live_id, channel_id):
        if 'ppv' not in vfilter:
            return True
        return vfilter['ppv'] == (channel_id is not None
                                  and self._niconico.is_ppv_live(
                                      live_id, channel_id))

    def iter_search(self, vfilter, fields=set()):
        search_fields = {'contentId', 'channelId'} | set(fields)
        iter_contents = self._niconico.contents_search(
            vfilter['q'],
            service='live',
            targets=vfilter['targets'],
            fields=search_fields,
            json_filter=self.contents_search_json_filter(vfilter),
            sort=vfilter['sort'])

        for content in iter_contents:
            if not self.match_ppv(vfilter, content['contentId'],
                                  content['channelId']):
                continue
            yield {k: v for k, v in content.items() if k in fields}

    def iter_search_all(self, fields=set()):
        for vfilter in self.filter_list:
            yield from self.iter_search(vfilter, fields=fields)

    def print(self, *args, **kwargs):
        kwargs['file'] = self.stdout
        print(*args, **kwargs)

    def print_err(self, *args, **kwargs):
        kwargs['file'] = self.stderr
        print(*args, **kwargs)

    def print_diff(self, ts_list_before, ts_list_after):
        for ts in ts_list_after:
            if ts['vid'] in (ts['vid'] for ts in ts_list_before):
                continue
            self.print('added: ' + ts['vid'] + ': ' + ts['title'])

        for ts in ts_list_before:
            if ts['vid'] in (ts['vid'] for ts in ts_list_after):
                continue
            self.print('removed: ' + ts['vid'] + ': ' + ts['title'])

    @_tsm_run
    def run_search_only(self, n):
        iter_search_all = self.iter_search_all(fields={'contentId', 'title'})
        iter_search_all = itertools.islice(iter_search_all, n)
        for content in iter_search_all:
            self.print(content['contentId'] + ': ' + content['title'])
        return 0

    @_tsm_run
    def run_auto_reserve(self):
        ts_list_before = self._niconico.ts_list()
        for content in self.iter_search_all(fields={'contentId'}):
            if content['contentId'] in (ts['vid'] for ts in ts_list_before):
                continue
            try:
                self.ts_register(content['contentId'])
            except TSNotSupported as e:
                if 'ts_not_supported' in self.warnings:
                    self.print_err('warning: {}'.format(e))
                continue
            except TSAlreadyRegistered:
                continue
            except TSRegistrationExpired as e:
                if 'ts_registration_expired' in self.warnings:
                    self.print_err('warning: {}'.format(e))
                continue
            except TSMaxReservation as e:
                if 'ts_max_reservation' in self.warnings:
                    self.print_err('warning: {}'.format(e))
                break

        ts_list_after = self._niconico.ts_list()
        self.print_diff(ts_list_before, ts_list_after)
        return 0
