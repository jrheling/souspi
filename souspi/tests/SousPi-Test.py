#!/usr/bin/python

import SousPi
import unittest
import time

class SousPi_Test(unittest.TestCase):
    
    def setUp(self):
        self.sp = SousPi.SousPi()

    def tearDown(self):
        self.sp.cleanup()

    def test_construct(self):
        self.assertIsInstance(self.sp, SousPi.SousPi)

    def test_init(self):
        self.assertEquals(self.sp.running, False)

    def test_window_size(self):
        self.sp._set_window_size(5)
        self.assertEquals(self.sp._window_size, 5)
        self.sp._set_window_size(8.0)
        self.assertEquals(self.sp._window_size, 8.0)
        self.sp._set_window_size("12")
        self.assertEquals(self.sp._window_size, 12.0)
        with self.assertRaises(ValueError):
            self.sp._set_window_size("lorem ipsum")
            self.sp._window_size = 0
            self.sp._window_size = -10

    def test_config_read(self):
        self.sp._configure()
        print "%s" % self.sp.p.Kp
        self.assertEquals(self.sp._window_size, 10)
        self.assertTrue(self.sp.p.Kp > 0)

    def test_setpoint(self):
        self.sp._configure()
        self.sp.setpoint = 5
        self.assertEquals(self.sp.setpoint, 5)
        self.sp.setpoint = 8.0
        self.assertEquals(self.sp.setpoint, 8.0)
        with self.assertRaises(SousPi.ImpossibleSetpointError):
            self.sp.setpoint = 0
            self.sp.setpoint = -3.2
            self.sp.setpoint = "foobarzle"
        
if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(SousPi_Test)
    unittest.TextTestRunner(verbosity=2).run(suite)
