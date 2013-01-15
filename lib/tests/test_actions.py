import fixtures
import libvirt
from libvirt import libvirtError
from testtools import TestCase
from testtools.matchers import Contains
import subprocess

from lib import actions
from lib.settings import settings
from lib.args import get_parser

class FakeConn(object):
    def __init__(self, raise_errors=[]):
        self._raise_errors = raise_errors

    def defineXML(self, arg):
        if 'defineXML' in self._raise_errors:
            raise libvirtError('Forced Error')
        pass

    def lookupByName(self, name):
        if 'lookupByName' in self._raise_errors:
            raise libvirtError('Forced Error')
        return None

class FakeLibvirtOpen(object):
    def __init__(self, testcase, raise_errors=[]):
        self._raise_errors = raise_errors
        self.testcase = testcase

    def __call__(self, qemu_path):
        self.testcase.assertEquals(settings.QEMU, qemu_path)
        return FakeConn(self._raise_errors)

class FakeCheckCall(object):
    def __call__(self, *args, **kwargs):
        pass

class TestActions(TestCase):

    def argv(self, cmd):
        tdir = self.useFixture(fixtures.TempDir()).path
        return ['bm_poseur', '--image-path', tdir, cmd]

    def _test_create_vm(self, mock_libv, assert_text, *extra_args):
        aobj = actions()
        parser = get_parser(aobj)
        argv = self.argv('create-vm')
        argv.extend(extra_args)
        mock_call = FakeCheckCall()
        self.useFixture(fixtures.MonkeyPatch('libvirt.open', mock_libv))
        self.useFixture(fixtures.MonkeyPatch('subprocess.check_call', mock_call))
        stdout = self.useFixture(fixtures.StringStream('stdout'))
        args = parser.parse_args(argv[1:])
        aobj.set_params(args)
        with fixtures.MonkeyPatch('sys.stdout', stdout.stream):
            args.func()
        self.assertThat(
            stdout.getDetails()['stdout'].as_text(), Contains(assert_text))

    def test_create_vm(self):
        mock_libv = FakeLibvirtOpen(self)
        self._test_create_vm(mock_libv, '1 vms have been created')

    def test_create_vm_ignore_existing(self):
        mock_libv = FakeLibvirtOpen(self, ['lookupByName'])
        self._test_create_vm(mock_libv, '1 vms have been created', '--ignore-existing')

    def test_create_vm_ignore_existing_error(self):
        mock_libv = FakeLibvirtOpen(self)
        self._test_create_vm(mock_libv, '0 vms have been created', '--ignore-existing')
