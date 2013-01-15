import libvirt
import mocker
from mocker import ANY
from testtools import TestCase
import tempfile
import shutil
import subprocess

from lib import actions
from lib.settings import settings
from lib.args import get_parser

class TestActions(TestCase):

    def setUp(self):
        super(TestActions, self).setUp()
        self.parser = get_parser()
        tdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tdir)
        self.argv = ['bm_poseur', '--image-path', tdir]

    def test_create_vms(self):
        self.argv.append('create-vm')
        m = mocker.Mocker()
        mock_libv = m.mock()
        mock_call = m.mock()
        save_open = libvirt.open
        save_ccall = subprocess.check_call
        libvirt.open = mock_libv
        subprocess.check_call = mock_call
        def _cleanup(sopen, ccall):
            libvirt.open = sopen
            subprocess.check_call = ccall
        self.addCleanup(_cleanup, save_open, save_ccall)
        mock_libv(settings.QEMU)
        mock_conn = m.mock()
        m.result(mock_conn)
        mock_call(ANY, shell=ANY)
        mock_call(ANY, shell=ANY)
        mock_conn.defineXML(ANY)
        mock_call(ANY, shell=ANY)
        mock_call(ANY, shell=ANY)
        m.replay()
        self.parser.parse_args(self.argv[1:])
        m.restore()
