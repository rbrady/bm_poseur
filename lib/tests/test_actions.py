import fixtures
import libvirt
from testtools import TestCase
import tempfile
import subprocess

from lib import actions
from lib.settings import settings
from lib.args import get_parser

class FakeConn(object):
    def defineXML(self, *args, **kwargs):
        pass

class FakeLibvirtOpen(object):
    def __call__(self, *args, **kwargs):
        return FakeConn()

class FakeCheckCall(object):
    def __call__(self, *args, **kwargs):
        pass

class TestActions(TestCase):

    def argv(self, cmd):
        tdir = self.useFixture(fixtures.TempDir()).path
        return ['bm_poseur', '--image-path', tdir, cmd]

    def test_create_vms(self):
        parser = get_parser()
        argv = self.argv('create-vm')
        mock_libv = FakeLibvirtOpen()
        mock_call = FakeCheckCall()
        self.useFixture(fixtures.MonkeyPatch('libvirt.open', mock_libv))
        self.useFixture(fixtures.MonkeyPatch('subprocess.check_call', mock_call))
        parser.parse_args(argv[1:])
