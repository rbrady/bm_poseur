from testtools import TestCase
from testtools.matchers import IsInstance
from argparse import ArgumentParser

from lib.args import get_parser
from lib.actions import actions

class TestArgs(TestCase):

    def test_get_parser(self):
        parser = get_parser(actions())
        self.assertThat(parser, IsInstance(ArgumentParser))
