from shared_bugzilla import zilla
import unittest

class TestMetadata(unittest.TestCase):
    """
    A simple test to ensure that metadata can be pulled from bugzilla
    """
    
    def test_version(self):
        zilla.get_version()
    
    def test_parameters(self):
        zilla.get_parameters()
    
    def test_extensions(self):
        zilla.get_extensions()
    
    def test_time(self):
        zilla.get_time()

if __name__ == "__main__":
    unittest.main()
