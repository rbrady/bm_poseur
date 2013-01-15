import fixtures
import libvirt
import mocker
from mocker import ANY
from testtools import TestCase
import tempfile
import subprocess

from lib import actions
from lib.settings import settings
from lib.args import get_parser

class TestActions(TestCase):

    def argv(self, cmd):
        tdir = self.useFixture(fixtures.TempDir()).path
        return ['bm_poseur', '--image-path', tdir, cmd]

    def test_create_vms(self):
        parser = get_parser()
        argv = self.argv('create-vm')
        m = mocker.Mocker()
        mock_libv = m.mock()
        mock_call = m.mock()
        self.addCleanup(m.restore)
        self.useFixture(fixtures.MonkeyPatch('libvirt.open', mock_libv))
        self.useFixture(fixtures.MonkeyPatch('subprocess.check_call', mock_call))
        mock_libv(settings.QEMU)
        mock_conn = m.mock()
        m.result(mock_conn)
        mock_call(ANY, shell=ANY)
        mock_call(ANY, shell=ANY)
        mock_conn.defineXML(ANY)
        mock_call(ANY, shell=ANY)
        mock_call(ANY, shell=ANY)
        m.replay()
        parser.parse_args(argv[1:])
