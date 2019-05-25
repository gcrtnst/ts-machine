import functools
import json
import re
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime

import dateutil.parser
import dateutil.tz
from bs4 import BeautifulSoup
from requests import Session

from . import utils
from .exceptions import (ContentSearchError, InvalidResponse, LoginFailed,
                         LoginRequired, NotFound, TSAlreadyRegistered,
                         TSNotSupported, TSReachedLimit, TSRegistrationExpired)


def _login_if_required(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except LoginRequired:
            if self.mail is None or self.password is None:
                raise
            self.login()
        try:
            return func(self, *args, **kwargs)
        except LoginRequired:
            raise LoginFailed
    return wrapper


def _contents_search_filters_data(filters):
    data = {}
    for field, value in filters.items():
        if isinstance(value, list):
            for i, v in enumerate(value):
                data['filters[' + field + '][' + str(i + 1) + ']'] = _contents_search_filters_value(v)
        elif isinstance(value, dict):
            for k, v in value.items():
                data['filters[' + field + '][' + k + ']'] = _contents_search_filters_value(v)
        else:
            data['filters[' + field + '][1]'] = _contents_search_filters_value(value)
    return data


def _contents_search_filters_value(value):
    if isinstance(value, datetime):
        return value.isoformat(timespec='seconds')
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if value is None:
        return 'null'
    return str(value)


class Niconico:
    def __init__(self):
        self.mail = None
        self.password = None
        self.context = None
        self.timeout = None
        self._session = Session()
        self._session.headers = {}

    @property
    def user_agent(self):
        return self._session.headers.get('User-Agent')

    @user_agent.setter
    def user_agent(self, value):
        self._session.headers['User-Agent'] = value

    @property
    def cookies(self):
        return self._session.cookies

    @cookies.setter
    def cookies(self, value):
        self._session.cookies = value

    def user_session(self):
        for cookie in self.cookies:
            if cookie.name == 'user_session' and cookie.domain == '.nicovideo.jp':
                return cookie.value
        return None

    def _http_get(self, *args, **kwargs):
        if 'timeout' not in kwargs or kwargs['timeout'] is None:
            kwargs['timeout'] = self.timeout
        return self._session.get(*args, **kwargs)

    def _http_post(self, *args, **kwargs):
        if 'timeout' not in kwargs or kwargs['timeout'] is None:
            kwargs['timeout'] = self.timeout
        return self._session.post(*args, **kwargs)

    def logout(self, timeout=None):
        self._http_get('https://secure.nicovideo.jp/secure/logout', timeout=timeout, allow_redirects=False).raise_for_status()

    def login(self, timeout=None):
        if self.mail is None or self.password is None:
            raise LoginFailed('mail or password not provided')

        self._http_post('https://account.nicovideo.jp/api/v1/login', data={
            'mail_tel': self.mail,
            'password': self.password,
        }, timeout=timeout, allow_redirects=False).raise_for_status()
        if self.user_session() is None:
            raise LoginFailed('mail or password is incorrect')

    def _ts_watch_num(self, vid, timeout=None):
        resp = self._http_post('https://live.nicovideo.jp/api/watchingreservation', data={
            'mode': 'watch_num',
            'vid': vid,
        }, timeout=timeout)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html5lib')

        tag = soup.select_one('#reserve > button')
        if tag is not None and 'onclick' in tag.attrs:
            pattern = re.escape(r"Nicolive.TimeshiftActions.doRegister('lv320142236','") + r'(?P<token>ulck_\d+)' + re.escape(r"')")
            match = re.search(pattern, tag.attrs['onclick'])
            if match:
                return match.group('token')

        tag = soup.select_one('body > div[class="ab inform"] > div.atxt > div.info > div > p')
        if tag is not None:
            # You need to log in to use the time shift reservation.
            if tag.text == '\u30bf\u30a4\u30e0\u30b7\u30d5\u30c8\u4e88\u7d04\u306e\u3054\u5229\u7528\u306f\u3001\u30ed\u30b0\u30a4\u30f3\u304c\u5fc5\u8981\u3067\u3059\u3002':
                raise LoginRequired('login is required for timeshift registration')

            # There are no target programs.
            if tag.text == '\u5bfe\u8c61\u756a\u7d44\u306f\u3042\u308a\u307e\u305b\u3093\u3002':
                raise NotFound('lv' + vid + ' not found')

            # I'm very sorry. A system error has occurred.
            if tag.text == '\u5927\u5909\u7533\u3057\u8a33\u3054\u3056\u3044\u307e\u305b\u3093\u3002\u30b7\u30b9\u30c6\u30e0\u30a8\u30e9\u30fc\u304c\u767a\u751f\u3057\u307e\u3057\u305f\u3002 ':
                raise NotFound('lv' + vid + ' not found')

            # This program is not time-shifted.
            if tag.text == '\u3053\u306e\u756a\u7d44\u306f\u30bf\u30a4\u30e0\u30b7\u30d5\u30c8\u306b\u5bfe\u5fdc\u3057\u3066\u3044\u307e\u305b\u3093\u3002':
                raise TSNotSupported('timeshift is not supported for lv' + vid)

            # It's already reserved.
            if tag.text == '\u65e2\u306b\u4e88\u7d04\u6e08\u307f\u3067\u3059\u3002':
                raise TSAlreadyRegistered('timeshift already registered for lv' + vid)

            # The application has expired.
            if tag.text == '\u7533\u3057\u8fbc\u307f\u671f\u9650\u5207\u308c\u3067\u3059\u3002':
                raise TSRegistrationExpired('timeshift registration expired for lv' + vid)

            # Time shift reserve limit reached.
            if tag.text == '\u30bf\u30a4\u30e0\u30b7\u30d5\u30c8\u306e\u4e88\u7d04\u4e0a\u9650\u306b\u9054\u3057\u307e\u3057\u305f\u3002':
                raise TSReachedLimit('timeshift reservation limit has been reached')
        raise InvalidResponse('failed to register timeshift with invalid response')

    def _ts_regist(self, vid, token, overwrite=False, timeout=None):
        resp = self._http_post('https://live.nicovideo.jp/api/watchingreservation', data={
            'mode': 'overwrite' if overwrite else 'regist',
            'vid': vid,
            'token': token,
        }, timeout=timeout)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, 'html5lib')
        if soup.select_one('#regist_finished') is not None:
            return

        # You need to log in to use the time shift reservation.
        tag = soup.select_one('body > div[class="ab inform"] > div.atxt > div.info > div > p')
        if tag is not None and tag.text == '\u30bf\u30a4\u30e0\u30b7\u30d5\u30c8\u4e88\u7d04\u306e\u3054\u5229\u7528\u306f\u3001\u30ed\u30b0\u30a4\u30f3\u304c\u5fc5\u8981\u3067\u3059\u3002':
            raise LoginRequired('login is required for timeshift registration')
        raise InvalidResponse('failed to register timeshift with invalid response')

    @_login_if_required
    def ts_register(self, live_id, timeout=None, overwrite=False):
        vid = str(utils.int_id('lv', live_id))
        token = self._ts_watch_num(vid, timeout)
        self._ts_regist(vid, token, overwrite, timeout)

    @_login_if_required
    def ts_list(self, timeout=None):
        resp = self._http_post('https://live.nicovideo.jp/api/watchingreservation', data={
            'mode': 'list',
        }, timeout=timeout)
        root = ET.fromstring(resp.text)
        if 'status' not in root.attrib:
            raise InvalidResponse('failed to get timeshift list with invalid response')
        if root.attrib['status'] == 'fail':
            raise LoginRequired('login is required to get timeshift list')
        if root.attrib['status'] != 'ok':
            raise InvalidResponse('failed to get timeshift list with unknown status ' + root.attrib['status'])
        return ['lv' + vid.text for vid in root.iterfind('./timeshift_reserved_list/vid')]

    def contents_search(self, q, service='video', targets=['title', 'description', 'tags'], fields=set(), filters={}, json_filter=None, sort='-viewCounter', timeout=None):
        service = urllib.parse.quote(service, safe='')
        data = {
            'q': q,
            'targets': ','.join((t.replace(',', '') for t in targets)),
            '_sort': sort,
            '_offset': 0,
        }
        if fields:
            data['fields'] = ','.join(fields)
        if filters:
            data.update(_contents_search_filters_data(filters))
        if json_filter is not None:
            data['jsonFilter'] = json.dumps(json_filter, allow_nan=False)
        if self.context is not None:
            data['_context'] = self.context

        total = 1600
        while data['_offset'] < total:
            resp = self._http_post('https://api.search.nicovideo.jp/api/v2/' + service + '/contents/search', data=data, timeout=timeout)
            resp_json = json.loads(resp.text)
            if 'meta' not in resp_json:
                raise InvalidResponse('contents search failed with invalid response')
            if resp_json['meta']['status'] != 200:
                raise ContentSearchError(resp_json['meta']['errorMessage'], code=resp_json['meta']['errorCode'])
            if not resp_json['data']:
                break

            for content in resp_json['data']:
                if 'startTime' in content:
                    content['startTime'] = dateutil.parser.isoparse(content['startTime'])
                if 'openTime' in content:
                    content['openTime'] = dateutil.parser.isoparse(content['openTime'])
                yield content

            data['_offset'] += len(resp_json['data'])
            if resp_json['meta']['totalCount'] < total:
                total = resp_json['meta']['totalCount']

    def is_ppv_live(self, live_id, channel_id, timeout=None):
        live_id = utils.str_id('lv', live_id)
        channel_id = utils.str_id('ch', channel_id)
        resp = self._http_get('https://ch.nicovideo.jp/ppv_live/' + channel_id + '/' + live_id, timeout=timeout)
        if resp.status_code == 404:
            return False
        resp.raise_for_status()
        return True

    def server_time(self, timeout=None):
        resp = self._http_post('https://api.ce.nicovideo.jp/api/v1/system.unixtime', timeout=timeout)
        resp.raise_for_status()
        return datetime.fromtimestamp(int(resp.text), tz=dateutil.tz.gettz())
