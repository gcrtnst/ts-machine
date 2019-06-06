import unittest
from datetime import datetime

from tsm import TSMachine


class TestTSMachine(unittest.TestCase):
    def test_contents_search_filters(self):
        tsm = TSMachine()
        tsm.filters = {
            'tags': 'ab c',
            'openBefore': '1d',
            'liveEndAfter': '30m',
            'scoreTimeshiftReservedMin': 10,
            'ppv': False
        }
        now = datetime(1, 1, 1)
        filters = tsm.contents_search_filters(now=now)
        self.assertEqual(filters, {
            'timeshiftEnabled': True,
            'tags': 'ab c',
            'openTime': {'lte': datetime(1, 1, 2)},
            'liveEndTime': {'gte': datetime(1, 1, 1, 0, 30)},
            'scoreTimeshiftReserved': {'gte': 10},
        })
