import unittest
from datetime import datetime
from unittest.mock import Mock, call

import niconico.client
import niconico.utils
from niconico.client import Niconico
from niconico.exceptions import InvalidContentID, LoginFailed, LoginRequired


class TestNiconico(unittest.TestCase):
    def test_login_if_required(self):
        n = Mock(spec_set=Niconico())
        n.mail = None
        n.password = None
        func = Mock()
        niconico.client._login_if_required(func)(n)
        self.assertEqual(n.mock_calls, [])
        self.assertEqual(func.mock_calls, [call(n)])

        n = Mock(spec_set=Niconico())
        n.mail = None
        n.password = None
        func = Mock(side_effect=LoginRequired)
        with self.assertRaises(LoginRequired):
            niconico.client._login_if_required(func)(n)
        self.assertEqual(n.mock_calls, [])
        self.assertEqual(func.mock_calls, [call(n)])

        n = Mock(spec_set=Niconico())
        n.mail = 'email@example.com'
        n.password = 'password'
        func = Mock(side_effect=[LoginRequired, None])
        niconico.client._login_if_required(func)(n)
        self.assertEqual(n.mock_calls, [call.login()])
        self.assertEqual(func.mock_calls, [call(n), call(n)])

        n = Mock(spec_set=Niconico())
        n.mail = 'email@example.com'
        n.password = 'password'
        func = Mock(side_effect=[LoginRequired, LoginRequired])
        with self.assertRaises(LoginFailed):
            niconico.client._login_if_required(func)(n)
        self.assertEqual(n.mock_calls, [call.login()])
        self.assertEqual(func.mock_calls, [call(n), call(n)])

    def test_contents_search_filters_data(self):
        filters = {
            'userId': 0,
            'channelId': [0, 1, 2],
            'startTime': {'gt': datetime(1, 1, 1), 'lt': datetime(1, 1, 2)},
        }
        data = {
            'filters[userId][1]': '0',
            'filters[channelId][1]': '0',
            'filters[channelId][2]': '1',
            'filters[channelId][3]': '2',
            'filters[startTime][gt]': '0001-01-01T00:00:00',
            'filters[startTime][lt]': '0001-01-02T00:00:00',
        }
        self.assertEqual(niconico.client._contents_search_filters_data(filters), data)

    def test_contents_search_filters_value(self):
        for c in [
                (datetime(1, 1, 1), '0001-01-01T00:00:00'),
                (True, 'true'),
                (False, 'false'),
                (None, 'null'),
                (0, '0'),
        ]:
            self.assertEqual(niconico.client._contents_search_filters_value(c[0]), c[1])

    def test_http_request(self):
        n = Niconico()
        n.timeout = None
        n._session = Mock(spec_set=n._session)
        n._http_request()
        self.assertEqual(n._session.mock_calls, [call.request(timeout=None)])

        n = Niconico()
        n.timeout = 1
        n._session = Mock(spec_set=n._session)
        n._http_request()
        self.assertEqual(n._session.mock_calls, [call.request(timeout=1)])

        n = Niconico()
        n.timeout = None
        n._session = Mock(spec_set=n._session)
        n._http_request(timeout=2)
        self.assertEqual(n._session.mock_calls, [call.request(timeout=2)])

        n = Niconico()
        n.timeout = 1
        n._session = Mock(spec_set=n._session)
        n._http_request(timeout=2)
        self.assertEqual(n._session.mock_calls, [call.request(timeout=2)])


class TestNiconicoUtils(unittest.TestCase):
    def test_parse_id(self):
        for c in [
                (10, (None, 10)),
                ('10', (None, 10)),
                ('lv10', ('lv', 10))]:
            self.assertEqual(niconico.utils.parse_id(c[0]), c[1])

        with self.assertRaises(InvalidContentID):
            niconico.utils.parse_id('lv')
