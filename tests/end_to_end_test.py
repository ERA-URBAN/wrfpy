import os
from os.path import dirname, abspath
import unittest
from wrfpy.configuration import configuration


class end2endtest(unittest.TestCase):
    def setUp(self):
        '''
        setup test environment
        '''
        # define test_data location
        self.test_data = os.path.join(dirname(abspath(__file__)), '..',
                                      'test_data')

    def test_01(self):
        '''
        Test single radar with 2 vertical levels
        '''
        results = {}
        results['suitename'] = 'test'
        results['basedir'] = './'
        results['init'] = True
        configuration(results)
        # test if config.json exists
        outfile = os.path.join(results['basedir'],
                               results['suitename'], 'config.json')
        self.assertEqual(os.path.exists(outfile), 1)


if __name__ == "__main__":
    unittest.main()
