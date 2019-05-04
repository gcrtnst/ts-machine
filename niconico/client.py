import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from functools import wraps
from urllib.parse import quote

from dateutil.parser import isoparse
from dateutil.tz import gettz
from requests import Session

from .exceptions import (ContentSearchError, InvalidContentID, InvalidResponse,
                         LoginFailed, LoginRequired, TSAlreadyRegistered,
                         TSNotSupported, TSReachedLimit, TSRegistrationExpired)


def _login_if_required(func):
    @wraps(func)
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


class Niconico:
    def __init__(self):
        self.mail = None
        self.password = None
        self.context = None
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
        for cookie in iter(self.cookies):
            if cookie.name == 'user_session' and cookie.domain == '.nicovideo.jp':
                return cookie.value
        return None

    def logout(self):
        self._session.get('https://secure.nicovideo.jp/secure/logout')

    def login(self):
        if self.mail is None or self.password is None:
            raise LoginFailed('mail or password not provided')

        self._session.post('https://account.nicovideo.jp/api/v1/login', data={
            'mail_tel': self.mail,
            'password': self.password,
        })
        if self.user_session() is None:
            raise LoginFailed('mail or password is incorrect')

    @_login_if_required
    def ts_register(self, live_id):
        vid = str(_int_id('lv', live_id))

        # get token
        resp = self._session.post('https://live.nicovideo.jp/api/watchingreservation', data={
            'mode': 'watch_num',
            'vid': vid,
        })
        resp.raise_for_status()
        match = re.search(r'ulck_\d+', resp.text)
        if not match:
            if resp.text.find('https://account.nicovideo.jp/login') != -1:
                raise LoginRequired('login is required for timeshift registration')
            if resp.text.find('\u3053\u306e\u756a\u7d44\u306f\u30bf\u30a4\u30e0\u30b7\u30d5\u30c8\u306b\u5bfe\u5fdc\u3057\u3066\u3044\u307e\u305b\u3093\u3002') != -1:
                raise TSNotSupported('timeshift is not supported for lv' + vid)
            if resp.text.find('http://live.nicovideo.jp/my') != -1:
                raise TSAlreadyRegistered('timeshift already registered for lv' + vid)
            if resp.text.find('\u7533\u3057\u8fbc\u307f\u671f\u9650\u5207\u308c\u3067\u3059\u3002') != -1:
                raise TSRegistrationExpired('timeshift registration expired for lv' + vid)
            if resp.text.find('\u30bf\u30a4\u30e0\u30b7\u30d5\u30c8\u306e\u4e88\u7d04\u4e0a\u9650\u306b\u9054\u3057\u307e\u3057\u305f\u3002') != -1:
                raise TSReachedLimit('timeshift reservation limit has been reached')
            raise InvalidResponse('failed to register timeshift with invalid response')
        token = match.group(0)

        # register
        resp = self._session.post('https://live.nicovideo.jp/api/watchingreservation', data={
            'mode': 'regist',
            'vid': vid,
            'token': token,
        })
        resp.raise_for_status()
        if resp.text.find('https://account.nicovideo.jp/login') != -1:
            raise LoginRequired('login is required for timeshift registration')
        if resp.text.find('regist_finished') == -1:
            raise InvalidResponse('failed to register timeshift with invalid response')

    @_login_if_required
    def ts_list(self):
        resp = self._session.post('https://live.nicovideo.jp/api/watchingreservation', data={
            'mode': 'list',
        })
        root = ET.fromstring(resp.text)
        if 'status' not in root.attrib:
            raise InvalidResponse('failed to get timeshift list with invalid response')
        if root.attrib['status'] == 'fail':
            raise LoginRequired('login is required to get timeshift list')
        if root.attrib['status'] != 'ok':
            raise InvalidResponse('failed to get timeshift list with unknown status ' + root.attrib['status'])

        ts_list = []
        for vid in root.iterfind('./timeshift_reserved_list/vid'):
            ts_list.append('lv' + vid.text)
        return ts_list

    @_login_if_required
    def ts_detail_list(self):
        resp = self._session.post('https://live.nicovideo.jp/api/watchingreservation', data={
            'mode': 'detaillist',
        })
        root = ET.fromstring(resp.text)
        if 'status' not in root.attrib:
            raise InvalidResponse('failed to get timeshift list with invalid response')
        if root.attrib['status'] == 'fail':
            raise LoginRequired('login is required to get timeshift list')
        if root.attrib['status'] != 'ok':
            raise InvalidResponse('failed to get timeshift list with unknown status ' + root.attrib['status'])

        items = []
        for xml_item in root.iterfind('./timeshift_reserved_detail_list/reserved_item'):
            expire = int(xml_item.find('expire').text)
            items.append({
                'vid': 'lv' + xml_item.find('vid').text,
                'title': xml_item.find('title').text,
                'status': xml_item.find('status').text,
                'unwatch': xml_item.find('unwatch').text != '0',
                'expire': datetime.fromtimestamp(expire, tz=gettz()) if expire != 0 else None,
            })
        return items

    def contents_search(self, q, service='video', targets=['title', 'description', 'tags'], fields=set(), filters={}, json_filter=None, sort='-viewCounter'):
        service = quote(service, safe='')
        data = {
            'q': q,
            'targets': ','.join((t.replace(',', '') for t in targets)),
            '_sort': sort,
            '_offset': 0,
        }
        if fields:
            data['fields'] = ','.join(fields)
        if filters:
            data.update(_filters_data(filters))
        if json_filter is not None:
            data['jsonFilter'] = json.dumps(json_filter, allow_nan=False)
        if self.context is not None:
            data['_context'] = self.context

        total = 1600
        while data['_offset'] < total:
            resp = self._session.post('https://api.search.nicovideo.jp/api/v2/' + service + '/contents/search', data=data)
            resp_json = json.loads(resp.text)
            if 'meta' not in resp_json:
                raise InvalidResponse('contents search failed with invalid response')
            if resp_json['meta']['status'] != 200:
                raise ContentSearchError(resp_json['meta']['errorMessage'], code=resp_json['meta']['errorCode'])
            if not resp_json['data']:
                break

            for content in resp_json['data']:
                if 'startTime' in content:
                    content['startTime'] = isoparse(content['startTime'])
                if 'openTime' in content:
                    content['openTime'] = isoparse(content['openTime'])
                yield content

            data['_offset'] += len(resp_json['data'])
            if resp_json['meta']['totalCount'] < total:
                total = resp_json['meta']['totalCount']

    def is_ppv_live(self, live_id, channel_id):
        live_id = _str_id('lv', live_id)
        channel_id = _str_id('ch', channel_id)
        resp = self._session.get('https://ch.nicovideo.jp/ppv_live/' + channel_id + '/' + live_id)
        if resp.status_code == 404:
            return False
        resp.raise_for_status()
        return True

    def server_time(self):
        resp = self._session.post('https://api.ce.nicovideo.jp/api/v1/system.unixtime')
        resp.raise_for_status()
        return datetime.fromtimestamp(int(resp.text), tz=gettz())


def _int_id(prefix, content_id):
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


def _str_id(prefix, content_id):
    return prefix + str(_int_id(prefix, content_id))


def _filters_data(filters):
    data = {}
    for field, value in filters.items():
        if isinstance(value, list):
            for i, v in enumerate(value):
                data['filters[' + field + '][' + str(i + 1) + ']'] = _filters_value(v)
        elif isinstance(value, dict):
            for k, v in value.items():
                data['filters[' + field + '][' + k + ']'] = _filters_value(v)
        else:
            data['filters[' + field + '][1]'] = _filters_value(value)
    return data


def _filters_value(value):
    if isinstance(value, datetime):
        return value.isoformat(timespec='seconds')
    if isinstance(value, bool):
        if value:
            return 'true'
        return 'false'
    if value is None:
        return 'null'
    return str(value)
