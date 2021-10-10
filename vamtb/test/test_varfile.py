"""Tests for varfile.
"""

import json
import os.path
import unittest

class VarFile(unittest.TestCase):
    def test_file(self):
        pass

    def test_basic(self):
        pass

def suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

if __name__ == '__main__':
    unittest.main(defaultTest='suite')