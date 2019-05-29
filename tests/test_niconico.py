import unittest

import niconico.utils
from niconico.exceptions import InvalidContentID


class TestNiconicoUtils(unittest.TestCase):
    def test_parse_id(self):
        for c in [
                {'in': 10, 'out': (None, 10)},
                {'in': '10', 'out': (None, 10)},
                {'in': 'lv10', 'out': ('lv', 10)}]:
            self.assertEqual(niconico.utils.parse_id(c['in']), c['out'])

        with self.assertRaises(InvalidContentID):
            niconico.utils.parse_id('lv')
