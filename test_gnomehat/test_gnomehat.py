import unittest
import imutil
import os
import numpy as np

from gnomehat.console.args import parse_gnomehat_args

class TestGnomehatCLI(unittest.TestCase):

    def setUp(self):
        for k in os.environ:
            if k.startswith('GNOMEHAT'):
                del os.environ[k]

    def tearDown(self):
        pass

    def test_parse_args(self):
        # gnomehat run somecommand runs that command
        argv = 'gnomehat run echo hello world'.split()
        command, args = parse_gnomehat_args(argv)
        assert command == 'run'
        assert args == ['echo', 'hello', 'world']

        argv = 'gnomehat run python main.py --eggs=5'.split()
        command, args = parse_gnomehat_args(argv)
        assert command == 'run'
        assert args == ['python', 'main.py', '--eggs=5']

        # Special case: 'gnomehat python' is an alias for 'gnomehat run python'
        argv = 'gnomehat python main.py --eggs=5'.split()
        command, args = parse_gnomehat_args(argv)
        assert command == 'run'
        assert args == ['python', 'main.py', '--eggs=5']

        argv = 'gnomehat -m my_comment_string python main.py --eggs=5'.split()
        command, args = parse_gnomehat_args(argv)
        assert command == 'run'
        assert args == ['-m', 'my_comment_string', 'python', 'main.py', '--eggs=5']


if __name__ == '__main__':
    unittest.main()
