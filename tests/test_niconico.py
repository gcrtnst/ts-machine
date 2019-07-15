import unittest
from unittest.mock import Mock, call

import tsm.niconico.client
import tsm.niconico.utils
from tsm.niconico.client import Niconico
from tsm.niconico.exceptions import (InvalidContentID, LoginFailed,
                                     LoginRequired)


class TestNiconico(unittest.TestCase):
    def test_login_if_required(self):
        n = Mock(spec_set=Niconico())
        n.mail = None
        n.password = None
        func = Mock()
        tsm.niconico.client._login_if_required(func)(n)
        self.assertEqual(n.mock_calls, [])
        self.assertEqual(func.mock_calls, [call(n)])

        n = Mock(spec_set=Niconico())
        n.mail = None
        n.password = None
        func = Mock(side_effect=LoginRequired)
        with self.assertRaises(LoginRequired):
            tsm.niconico.client._login_if_required(func)(n)
        self.assertEqual(n.mock_calls, [])
        self.assertEqual(func.mock_calls, [call(n)])

        n = Mock(spec_set=Niconico())
        n.mail = 'email@example.com'
        n.password = 'password'
        func = Mock(side_effect=[LoginRequired, None])
        tsm.niconico.client._login_if_required(func)(n)
        self.assertEqual(n.mock_calls, [call.login()])
        self.assertEqual(func.mock_calls, [call(n), call(n)])

        n = Mock(spec_set=Niconico())
        n.mail = 'email@example.com'
        n.password = 'password'
        func = Mock(side_effect=[LoginRequired, LoginRequired])
        with self.assertRaises(LoginFailed):
            tsm.niconico.client._login_if_required(func)(n)
        self.assertEqual(n.mock_calls, [call.login()])
        self.assertEqual(func.mock_calls, [call(n), call(n)])

    def test_http_request(self):
        n = Niconico()
        n.timeout = None
        n._session = Mock(spec_set=n._session)
        n._http_request('method', 'url')
        self.assertEqual(n._session.mock_calls, [
                         call.request('method', 'url', timeout=None)])

        n = Niconico()
        n.timeout = 1
        n._session = Mock(spec_set=n._session)
        n._http_request('method', 'url')
        self.assertEqual(n._session.mock_calls, [
                         call.request('method', 'url', timeout=1)])

        n = Niconico()
        n.timeout = None
        n._session = Mock(spec_set=n._session)
        n._http_request('method', 'url', timeout=2)
        self.assertEqual(n._session.mock_calls, [
                         call.request('method', 'url', timeout=2)])

        n = Niconico()
        n.timeout = 1
        n._session = Mock(spec_set=n._session)
        n._http_request('method', 'url', timeout=2)
        self.assertEqual(n._session.mock_calls, [
                         call.request('method', 'url', timeout=2)])

    def test_login(self):
        n = Niconico()
        n.mail = None
        n.password = None
        n._http_request = Mock(spec_set=n._http_request)
        with self.assertRaises(LoginFailed):
            n.login()
        self.assertEqual(n._http_request.mock_calls, [])

        resp = Mock()
        resp.cookies = []
        n = Niconico()
        n.mail = 'mail@example.com'
        n.password = 'password'
        n._http_request = Mock(spec_set=n._http_request, return_value=resp)
        with self.assertRaises(LoginFailed):
            n.login()
        self.assertEqual(n._http_request.mock_calls, [
            call('post', 'https://account.nicovideo.jp/api/v1/login', data={
                'mail_tel': 'mail@example.com',
                'password': 'password',
            }, allow_redirects=False)])
        self.assertEqual(resp.mock_calls, [call.raise_for_status()])

        cookie = Mock()
        cookie.name = 'user_session'
        resp = Mock()
        resp.cookies = [cookie]
        n = Niconico()
        n.mail = 'mail@example.com'
        n.password = 'password'
        n._http_request = Mock(spec_set=n._http_request, return_value=resp)
        n.login()
        self.assertEqual(n._http_request.mock_calls, [
            call('post', 'https://account.nicovideo.jp/api/v1/login', data={
                'mail_tel': 'mail@example.com',
                'password': 'password',
            }, allow_redirects=False)])
        self.assertEqual(resp.mock_calls, [call.raise_for_status()])


class TestNiconicoUtils(unittest.TestCase):
    def test_parse_id(self):
        for c in [
                (10, (None, 10)),
                ('10', (None, 10)),
                ('lv10', ('lv', 10))]:
            self.assertEqual(tsm.niconico.utils.parse_id(c[0]), c[1])

        with self.assertRaises(InvalidContentID):
            tsm.niconico.utils.parse_id('lv')
