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

    def test_contents_search_filters_value(self):
        for c in [
                (datetime(1, 1, 1), '0001-01-01T00:00:00'),
                (True, 'true'),
                (False, 'false'),
                (None, 'null'),
                (0, '0'),
        ]:
            self.assertEqual(niconico.client._contents_search_filters_value(c[0]), c[1])


class TestNiconicoUtils(unittest.TestCase):
    def test_parse_id(self):
        for c in [
                (10, (None, 10)),
                ('10', (None, 10)),
                ('lv10', ('lv', 10))]:
            self.assertEqual(niconico.utils.parse_id(c[0]), c[1])

        with self.assertRaises(InvalidContentID):
            niconico.utils.parse_id('lv')
