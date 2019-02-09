import unittest
import imutil
import os
import numpy as np

from gnomehat.console.args import parse_gnomehat_args
from gnomehat.console import run

class TestGnomehatCLI(unittest.TestCase):

    def setUp(self):
        for k in os.environ:
            if k.startswith('GNOMEHAT'):
                del os.environ[k]

    def tearDown(self):
        pass

    def test_parse_args(self):
        # Test that `gnomehat start` runs the `start` command, etc.
        argv = 'gnomehat run echo hello world'.split()
        command, args = parse_gnomehat_args(argv)
        assert command == 'run'
        assert args == ['echo', 'hello', 'world']

        argv = 'gnomehat run echo hello world'.split()
        command, args = parse_gnomehat_args(argv)
        assert command == 'run'
        assert args == ['echo', 'hello', 'world']

        # The gnomehat run command takes variable arguments after "run"
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

    def test_parse_run_args(self):
        # Test that gnomehat run works with arbitrary arguments
        args = ['python', 'main.py', '--eggs=5']
        options = run.parse_args(args)
        assert options['executable'] == 'python'
        assert options['args'] == ['main.py', '--eggs=5']

        # Test that gnomehat_run properly separates gnomehat args from command args
        args = ['-m', 'my_comment_string', 'python', 'main.py', '--eggs=5']
        options = run.parse_args(args)
        assert options['notes'] == 'my_comment_string'
        assert options['executable'] == 'python'
        assert options['args'] == ['main.py', '--eggs=5']



if __name__ == '__main__':
    unittest.main()
