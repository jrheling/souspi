#!/usr/bin/python

# test the string formatting solution proposed in 
#     http://stackoverflow.com/questions/7407766/format-a-number-containing-a-decimal-point-with-leading-zeroes
# to make sure it does what I think it does (on a wide variety of input)

import unittest

def fmt(f):
    """ Take a number, and return a string with 3 digits before the decimal and at least 2 after.
    
        It really seems like there must be a way to do this with printf.
    """
    rstr = "%03d" % f + str(f%1)[1:]
    try:
        dot_pos = rstr.index('.')
    except ValueError:
        # if there is no decimal part, add one
        rstr += ".00"  
    else:
        ## if there's just one digit in the decimal part, add a zero
        if (len(rstr) - dot_pos) < 3:
            rstr += "0"
    return rstr

class StrFormat_Test(unittest.TestCase):
    
    def setUp(self):
        pass
#        self.fmt =  lambda x : "%03d" % x + str(x%1)[1:]
    
    def test_format(self):
        samples = [ (3.158,"003.158"),
                    (0,"000.00"),
                    (213,"213.00"),
                    (421.321,"421.321"),
                    (.3,"000.30"),
                    (0.3,"000.30"),
                    (1.,"001.00"),
                    (1.1,"001.10")
                  ]
        for (f,s) in samples:
            self.assertEquals(s, fmt(f))
#        self.assertEquals("003.158", self.fmt(3.158))
        
if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(StrFormat_Test)
    unittest.TextTestRunner(verbosity=2).run(suite)
