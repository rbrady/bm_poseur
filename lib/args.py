# Copyright (c) 2012 Hewlett-Packard Development Company, L.P.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import argparse
from textwrap import dedent

from settings import settings

def get_parser(actions):
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter,
        description=dedent("""\
                            This is a CLI utility to provide devstack with virtualized resources
                            so that the baremetal hypervisor can be exercised, without having
                            actual physical hardware available.


                            Available Commands:

                            create-vm:
                               creates a VM and attaches it to the specified bridge

                            destroy-vm:
                               Destroys all VMs that were created

                            create-bridge:
                               creates network bridge and assigns IP and route

                            destroy-bridge:
                               destroys a bridge

                            get-macs:
                               returns MAC addresses of VMs that have been started

                            """),
        epilog=dedent("""\
                    Usage:

                    BareMetal Bridge:
                    Configure access to the virtual baremetal LAN for the bootstrap VM.
                    The default will do nothing and error, as changing your machine
                    config can be considered unfriendly. Passing -y will trigger the
                    demo mode where a local bridge called 'br999' with no external
                    ports connected is created, which as many 'bare metal' virtual
                    machines as you want can be connected to - this is the device that
                    configure-bootstrap-vm uses by default.

                    If you are provising actual hardware, you will want to add actual
                    physical ports (e.g. eth1) by passing '--with-port=eth1' to this
                    script.

                    If you only have one ethernet port in your machine, you will want
                    to migrate your networking configuration to a bridge before running
                    this script, and then pass '--with-port=br0' (or whatever port
                    you chose). In future reconfiguring your local networking may be
                    available as an automated step.   \n\n\n """))


    # output options
    parser.add_argument('--verbose', '-v', action='count')
    parser.add_argument('--silent', '-s', action='store_true')

    
    # all paramaters can be overridden

    parser.add_argument('--vms', nargs='?', type=int,
          default=settings.VMS,
          help='Number of vm\'s you wish to create. Default: %s' % settings.VMS)
    parser.add_argument('--arch', nargs='?',
          default=settings.ARCH,
          help='CPU architecture for the BM. Default: %s' % settings.ARCH,
          choices=['i686','x86_64'])
    parser.add_argument('--engine', nargs='?',
          default=settings.ENGINE,
          help='Default: %s' % settings.ENGINE,
          choices=['qemu','kvm'])
    parser.add_argument('--max-mem', nargs='?', type=int,
          default=settings.MAX_MEM,
          help='Default: %s' % settings.MAX_MEM)
    parser.add_argument('--cpus', nargs='?', type=int,
          default=settings.CPUS,
          help='Default: %s' % settings.CPUS)
    parser.add_argument('--qemu', nargs='?',
          default=settings.QEMU,
          help='Qemu address for lib virt (%s)' % settings.QEMU)
    parser.add_argument('--prefix', nargs='?',
          default=settings.PREFIX,
          help='Base name of virtual machines. Default: %s' % settings.PREFIX)
    parser.add_argument('--image-path', nargs='?',
          default=settings.IMAGE_PATH,
          help='Location to store virtual disk images. Default: %s' % settings.IMAGE_PATH)
    parser.add_argument('--disk-size', nargs='?',
          default=settings.DISK_SIZE,
          help='Disk image size. Default: %s' % settings.DISK_SIZE)
    parser.add_argument('--template-xml', nargs='?',
          default=settings.TEMPLATE_XML,
          help='Template XML file. Default: %s' % settings.TEMPLATE_XML)
    
    
    
    parser.add_argument('--bridge', nargs='?',
          default=settings.BRIDGE,
          help='Name of network bridge to create. Default: %s' % settings.BRIDGE)
    parser.add_argument('--bridge-ip', nargs='?',
          default=settings.BRIDGE_IP,
          help='IP address to assign to the bridge. Default: %s' % settings.BRIDGE_IP)
    parser.add_argument('--bridge-port', nargs='?', action="append",
          help='Network port(s) to add to the bridge. Optional.',
          default=[]) # Yes its mutable, don't reuse the parser.
    
    parser.add_argument('--network-config','-f',
          default='/etc/network/interfaces',
          help='Network config file to extend.')

    subparsers = parser.add_subparsers()
    parser_create_vm = subparsers.add_parser('create-vm')
    parser_create_vm.set_defaults(func=actions.create_vm)
    parser_destroy_vm = subparsers.add_parser('destroy-vm')
    parser_destroy_vm.set_defaults(func=actions.destroy_vm)
    parser_create_bridge = subparsers.add_parser('create-bridge')
    parser_create_bridge.set_defaults(func=actions.create_bridge)
    parser_destroy_bridge = subparsers.add_parser('destroy-bridge')
    parser_destroy_bridge.set_defaults(func=actions.destroy_bridge)
    parser_get_macs = subparsers.add_parser('get-macs')
    parser_get_macs.set_defaults(func=actions.get_macs)

    return parser
