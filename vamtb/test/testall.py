import os
import re
import sys
import unittest

pkgpath = os.path.dirname(os.path.dirname(os.path.realpath(__file__))) or '..'
sys.path.insert(0, pkgpath)

def suite():
    s = unittest.TestSuite()
    # Get the suite() of every module in this directory beginning with
    # "test_".
    for fname in os.listdir(os.path.join(pkgpath, 'test')):
        match = re.match(r'(test_\S+)\.py$', fname)
        if match:
            modname = match.group(1)
            s.addTest(__import__(modname).suite())
    return s


if __name__ == '__main__':
    unittest.main(defaultTest='suite')