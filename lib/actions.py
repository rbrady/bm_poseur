#!/usr/bin/env python
#
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

import libvirt
from libvirt import libvirtError
import argparse
import time
import os.path
import sys
import subprocess
from textwrap import dedent
import re
from lxml import objectify
from collections import defaultdict

BRIDGE_TEMPLATE = dedent(  """\

                           # bm_poseur bridge
                           auto %(bridge)s
                           iface %(bridge)s inet manual
                             bridge_ports %(ports)s   #bmposeur

                           """)


class actions(object):
    def __init__(self):
        self._conn = None
        self.params = None

    @property
    def conn(self):
        assert self.params
        if self._conn is None:
            self._conn=libvirt.open(self.params.qemu)
        return self._conn

    def _print(self, output, verbose=False):
        """ print wrapper so -v and -s can be respected """
        if not self.params.silent:
            if verbose is False:
                print(output)
            elif verbose is True and self.params.verbose > 0:
                print(output)

    def set_params(self, params):
        self.params = params

    def get_macs(self):
        """ This returns the mac addresses  xx:xx:xx,yy:yy:yy aa:aa:aa,bb:bb:bb """
        output=''
        domains=self.conn.listDefinedDomains()

        for domain in domains:
            if not domain.find(self.params.prefix) == -1:
               _xml = objectify.fromstring(self.conn.lookupByName(domain).XMLDesc(0))
               
               output += "%s" % _xml.devices.interface[0].mac.attrib.get("address")
               output += ",%s " % _xml.devices.interface[1].mac.attrib.get("address")
               
        print '%s' % output.strip(' ')


    def destroy_bridge(self):
        """ This destroys the bridge """
        self._print("reading network config file", True)

        # remove the route first
        idx=self.params.bridge_ip.rindex('.')
        net=self.params.bridge_ip[0:idx] + ".0"
        subprocess.check_call('route del -net %s netmask 255.255.255.0' % net, shell=True)

        # take the bridge down
        subprocess.check_call('ifdown %s' % self.params.bridge, shell=True)

        network_file = open(self.params.network_config, 'r').read()
        ports = " ".join(self.params.bridge_port) or "none"
        to_remove = BRIDGE_TEMPLATE % dict(bridge=self.params.bridge, ports=ports)
        to_remove = to_remove.strip().splitlines()

        self._print("clearing bridge", True)
        for line in to_remove:
            network_file = network_file.replace(line,'')

        self._print("writing changed network config file", True)
        outf = open( self.params.network_config , "w")
        outf.write(network_file.strip())
        outf.close()

        self._print("removing dnsmasq exclusion file", True)
        try:
            os.remove('/etc/dnsmasq.d/%s' % self.params.bridge)
        except:
            self._print("dnsmasq exclusion missing.", True)

        self._print('bridge %s destroyed' % self.params.bridge )

    def is_already_bridge(self):
        """ returns t/f if a bridge exists or not """
        network_file = open(self.params.network_config, 'r').read()
        if network_file.find(self.params.bridge) == -1:
            return False
        else:
            return True


    def create_bridge(self):
        """ this creates a bridge """

        if self.is_already_bridge():
            print('bridge already exists')
            return

        self._print("Creating bridge interface %(bridge)s." %
            dict(bridge=self.params.bridge), verbose=True)

        ports = " ".join(self.params.bridge_port) or "none"

        self._print("   Writing new stanza for bridge interface %(bridge)s." %
            dict(bridge=self.params.bridge), verbose=True)

        with file(self.params.network_config, 'ab') as outf:
            outf.seek(0, 2)
            outf.write(BRIDGE_TEMPLATE % dict(bridge=self.params.bridge, ports=ports))

        self._print("  Wrote new stanza for bridge interface %s." %
            self.params.bridge, verbose=True)

        self._print("   Writing dnsmasq.d exclusion file.", verbose=True)

        with file('/etc/dnsmasq.d/%(bridge)s' % dict(bridge=self.params.bridge), 'wb') as outf:
            outf.write('bind-interfaces\nexcept-interface=%(bridge)s\n' %
                dict(bridge=self.params.bridge))

        self._print ("    Wrote dnsmasq.d exclusion file /etc/dnsmasq.d/%s." %
            self.params.bridge, verbose=True)

        self._print('bring bridge online')
        subprocess.check_call('ifup %s ' % self.params.bridge , shell=True)
        if self.params.bridge_ip and self.params.bridge_ip.lower() != 'none':
            # XXX: This should change the stanza rather than calling ip
            self._print('Assigning IP %s to bridge' % self.params.bridge_ip)
            subprocess.check_call('ip addr add dev %s local %s/24 scope global' %
                   (self.params.bridge, self.params.bridge_ip),
                   shell=True)

        #idx=self.params.bridge_ip.rindex('.')
        #net=self.params.bridge_ip[0:idx] + ".0"
        #self._print('Adding route for bridge network')
        #subprocess.check_call('route add -net %s netmask 255.255.255.0 %s' %
        #      (net, self.params.bridge),
        #      shell=True)

    def load_xml(self, name, image):
        """Loads the xml file and evals it with the right settings"""
        self._print('load_xml called')

        template_xml = open(self.params.template_xml, 'r').read()

        return template_xml % dict( engine=self.params.engine,
                                    arch=self.params.arch,
                                    bridge=self.params.bridge,
                                    name=name,
                                    max_mem=self.params.max_mem,
                                    cpus=self.params.cpus,
                                    image=image )


    def destroy_vm(self):
        """ clears out vms """
        self._print('Deleting VMs')

        for domain in self.conn.listDefinedDomains():
            if not domain.find(self.params.prefix) == -1:
                dom = self.conn.lookupByName(domain)
                self._print("Found %s, deleting it" % domain)
                if dom.isActive():
                    dom.destroy()
                dom.undefine()

        self._print("Deleting disk images from %s" % self.params.image_path)
        cmd = "rm -rf %s*" % self.params.image_path
        subprocess.check_call(cmd, shell=True)


    def create_vm(self):
        """ creates the first vm """
        self._print('create called')

        if not os.path.isdir(self.params.image_path):
                os.makedirs(self.params.image_path)

        for i in range(self.params.vms):
            name = "%s%s" % (self.params.prefix , str(i))
            image = "%s%s.img" % (self.params.image_path, name)
            subprocess.check_call("sudo rm -f %s" % image, shell=True)
            cmd = "kvm-img create -f raw %s %s" % (image, self.params.disk_size)
            try:
                subprocess.check_call(cmd, shell=True)
            except subprocess.CalledProcessError:
                if self.params.ignore_existing:
                    continue
                raise

            try:
                self.conn.defineXML(self.load_xml(name,image))
            except libvirtError:
                if self.params.ignore_existing:
                    continue
                raise
                

        self._print('Fixing permissions and ownership', verbose=True)
        cmd = 'chmod 644 %s*' % self.params.image_path
        return_code = subprocess.check_call(cmd, shell=True)

        cmd = 'sudo chown libvirt-qemu %s*' % self.params.image_path
        subprocess.check_call(cmd, shell=True)

        self._print('%s vms have been created!' % str(self.params.vms))


    def stop_all(self):
        """ stop_all vms TODO"""
        self._print('stop_all called')


    def start_all(self):
        """ starts vms TODO"""
        self._print('start_all called')
        '''
        # start them
        print "Starting all node(s)"
        for node_name, node in vms.iteritems():
            print "Starting node ", node_name
            node.create()
            print "pausing ... "
            time.sleep(start_delay)
        '''


