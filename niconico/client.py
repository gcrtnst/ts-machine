import functools
import json
import re
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime

import dateutil.parser
import requests
from bs4 import BeautifulSoup
from requests import Session

from . import utils
from .exceptions import (CommunicationError, ContentSearchError,
                         InvalidResponse, LoginFailed, LoginRequired, NotFound,
                         Timeout, TSAlreadyRegistered, TSMaxReservation,
                         TSNotSupported, TSRegistrationExpired)


def _http_raise_for_status(resp):
    try:
        resp.raise_for_status()
    except requests.HTTPError as e:
        raise CommunicationError(e)


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
            raise LoginFailed('login failed for unknown reason')
    return wrapper


class Niconico:
    _re_ts_watch_num = re.compile(re.escape(r"Nicolive.TimeshiftActions.doRegister('lv") + '(?P<vid>[0-9]+)' + re.escape("','") + r'(?P<token>ulck_[0-9]+)' + re.escape(r"')"))
    _re_server_time = re.compile(re.escape(r'servertime=') + r'(?P<time>[0-9]+)')

    def __init__(self):
        self.mail = None
        self.password = None
        self.context = None
        self.timeout = None
        self.tz = None
        self._session = Session()

    @property
    def user_agent(self):
        return self._session.headers.get('User-Agent')

    @user_agent.setter
    def user_agent(self, value):
        if value is None:
            if 'User-Agent' in self._session.headers:
                del self._session.headers['User-Agent']
            return
        self._session.headers['User-Agent'] = value

    @property
    def cookies(self):
        return self._session.cookies

    @cookies.setter
    def cookies(self, value):
        self._session.cookies = value

    def close_connection(self):
        return self._session.close()

    def __enter__(self):
        self._session.__enter__()
        return self

    def __exit__(self, *args):
        return self._session.__exit__(*args)

    def _http_request(self, method, url, *args, **kwargs):
        if 'timeout' not in kwargs or kwargs['timeout'] is None:
            kwargs['timeout'] = self.timeout
        try:
            return self._session.request(method, url, *args, **kwargs)
        except requests.Timeout:
            raise Timeout('connection to ' + url + ' timed out')
        except (requests.ConnectionError, requests.HTTPError, requests.TooManyRedirects) as e:
            raise CommunicationError(e)

    def _http_get(self, *args, **kwargs):
        return self._http_request('get', *args, **kwargs)

    def _http_post(self, *args, **kwargs):
        return self._http_request('post', *args, **kwargs)

    def logout(self):
        resp = self._http_get('https://secure.nicovideo.jp/secure/logout', allow_redirects=False)
        _http_raise_for_status(resp)

    def login(self):
        if self.mail is None or self.password is None:
            raise LoginFailed('mail or password not provided')

        resp = self._http_post('https://account.nicovideo.jp/api/v1/login', data={
            'mail_tel': self.mail,
            'password': self.password,
        }, allow_redirects=False)
        _http_raise_for_status(resp)
        for cookie in resp.cookies:
            if cookie.name == 'user_session' or cookie.name == 'user_session_secure':
                return
        raise LoginFailed('mail or password is incorrect')

    def _ts_watch_num(self, vid):
        resp = self._http_post('https://live.nicovideo.jp/api/watchingreservation', data={
            'mode': 'watch_num',
            'vid': vid,
        })
        _http_raise_for_status(resp)
        soup = BeautifulSoup(resp.text, 'html5lib')

        tag = soup.select_one('#reserve > button')
        if tag is not None and 'onclick' in tag.attrs:
            match = self._re_ts_watch_num.search(tag.attrs['onclick'])
            if match and match.group('vid') == vid:
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

        tag = soup.select_one('body > div[class="ab inform"] > div.atxt > div.info > p')
        if tag is not None:
            # Time shift reserve limit reached.
            if tag.text == '\u30bf\u30a4\u30e0\u30b7\u30d5\u30c8\u306e\u4e88\u7d04\u4e0a\u9650\u306b\u9054\u3057\u307e\u3057\u305f\u3002':
                raise TSMaxReservation('max timeshift reservation exceeded')

        tag = soup.select_one('#reserve > a > span')
        if tag is not None and tag.text == '\u8996\u8074\u3059\u308b':  # watch
            raise TSAlreadyRegistered('timeshift already registered for lv' + vid)
        raise InvalidResponse('failed to register timeshift for lv' + vid + ' with invalid response')

    def _ts_regist(self, vid, token, overwrite=False):
        resp = self._http_post('https://live.nicovideo.jp/api/watchingreservation', data={
            'mode': 'overwrite' if overwrite else 'regist',
            'vid': vid,
            'token': token,
        })
        _http_raise_for_status(resp)

        soup = BeautifulSoup(resp.text, 'html5lib')
        if soup.select_one('#regist_finished') is not None:
            return

        tag = soup.select_one('body > div[class="ab inform"] > div.atxt > div.info > div > p')
        if tag is not None:
            # You need to log in to use the time shift reservation.
            if tag.text == '\u30bf\u30a4\u30e0\u30b7\u30d5\u30c8\u4e88\u7d04\u306e\u3054\u5229\u7528\u306f\u3001\u30ed\u30b0\u30a4\u30f3\u304c\u5fc5\u8981\u3067\u3059\u3002':
                raise LoginRequired('login is required for timeshift registration')
        if soup.select_one('#overwrite') is not None:
            raise TSMaxReservation('max timeshift reservation exceeded')
        raise InvalidResponse('failed to register timeshift for lv' + vid + ' with invalid response')

    @_login_if_required
    def ts_register(self, live_id, overwrite=False):
        vid = str(utils.int_id('lv', live_id))
        token = self._ts_watch_num(vid)
        self._ts_regist(vid, token, overwrite)

    @_login_if_required
    def ts_list(self):
        resp = self._http_post('https://live.nicovideo.jp/api/watchingreservation', data={
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
                'expire': datetime.fromtimestamp(expire, tz=self.tz) if expire != 0 else None,
            })
        return items

    def contents_search(self, q, service='video', targets=['title', 'description', 'tags'], fields=set(), json_filter=None, sort='-viewCounter'):
        service = urllib.parse.quote(service, safe='')
        data = {
            'q': q,
            'targets': ','.join((t.replace(',', '') for t in targets)),
            '_sort': sort,
            '_offset': 0,
        }
        if fields:
            data['fields'] = ','.join(fields)
        if json_filter is not None:
            data['jsonFilter'] = json.dumps(json_filter, allow_nan=False)
        if self.context is not None:
            data['_context'] = self.context

        total = 1600
        while data['_offset'] < total:
            resp = self._http_post('https://api.search.nicovideo.jp/api/v2/' + service + '/contents/search', data=data)
            resp_json = json.loads(resp.text)
            if 'meta' not in resp_json:
                raise InvalidResponse('contents search failed with invalid response')
            if resp_json['meta']['status'] != 200:
                raise ContentSearchError(resp_json['meta']['errorCode'] + ': ' + resp_json['meta']['errorMessage'], meta=resp_json['meta'])
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

    def is_ppv_live(self, live_id, channel_id):
        live_id = utils.str_id('lv', live_id)
        channel_id = utils.str_id('ch', channel_id)
        resp = self._http_get('https://ch.nicovideo.jp/ppv_live/' + channel_id + '/' + live_id)
        if resp.status_code == 404:
            return False
        _http_raise_for_status(resp)
        return True

    def server_time(self):
        resp = self._http_get('https://live.nicovideo.jp/api/getservertime')
        _http_raise_for_status(resp)

        match = self._re_server_time.search(resp.text)
        if not match:
            raise InvalidResponse('failed to get server time with invalid response')
        timestr = match.group('time')
        return datetime.fromtimestamp(int(timestr), tz=self.tz)
