import fixtures
import libvirt
from testtools import TestCase
import tempfile
import subprocess

from lib import actions
from lib.settings import settings
from lib.args import get_parser

class FakeConn(object):
    def defineXML(self, arg):
        pass

class FakeLibvirtOpen(object):
    def __init__(self, testcase):
        self.testcase = testcase

    def __call__(self, qemu_path):
        self.testcase.assertEquals(settings.QEMU, qemu_path)
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
        mock_libv = FakeLibvirtOpen(self)
        mock_call = FakeCheckCall()
        self.useFixture(fixtures.MonkeyPatch('libvirt.open', mock_libv))
        self.useFixture(fixtures.MonkeyPatch('subprocess.check_call', mock_call))
        parser.parse_args(argv[1:])
