#!/usr/bin/python

import TempTracker
import unittest
import random
from w1thermsensor import W1ThermSensor


class TempTracker_Test(unittest.TestCase):
    
    def setUp(self):
        self.tt = TempTracker.TempTracker("/tmp")

    def test_construct(self):
        self.assertIsInstance(self.tt, TempTracker.TempTracker)
    
    def test_init(self):
        self.assertEquals(self.tt.unit, W1ThermSensor.DEGREES_C)

    def test_unit(self):
        self.tt.unit = W1ThermSensor.DEGREES_F
        self.assertEquals(self.tt.unit, self.tt.DEGREES_F)

    def test_bad_unit(self):
        with self.assertRaises(W1ThermSensor.UnsupportedUnitError):
            self.tt.unit = "foobar"
        
    def test_dir(self):
        self.tt.directory = "/tmp"
        with self.assertRaises(TempTracker.TempTrackerDirNotWritable):
            self.tt.directory = "/foo/bar/baz/nosuchdir/is/likely/to/exist"
        
    def test_commit(self):
        self.tt.directory = "/tmp"
        self.tt._commit_value(30)
        
if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TempTracker_Test)
    unittest.TextTestRunner(verbosity=2).run(suite)
