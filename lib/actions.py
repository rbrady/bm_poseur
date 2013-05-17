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
import argparse
import time
import os.path
import sys
import subprocess
from textwrap import dedent
import re
from lxml import objectify
from lxml import etree
from collections import defaultdict

def call(*args, **kwargs):
    """subprocess.call with error checking."""
    assert not subprocess.call(*args, **kwargs)


class actions(argparse.Action):
    """ david please comment this """
    # vm reference object
    vms = {}
    settings = None
    conn = None
    xml_template = None

    def __call__(self, parser, params, values, option_string=None, **kwargs):
        """Triggered by -c command line argument """
        self.params = params
        setattr(self.params, self.dest, values)

        self._print(self.params, verbose=True)

        self.conn=libvirt.open(self.params.qemu)

        # action function mapping
        actions = { 'create-vm' : self.create_vms,
                    'destroy-vm' : self.destroy_vms,
                    'create-bridge' : self.create_bridge,
                    'destroy-bridge' : self.destroy_bridge,
                    'get-macs' : self.get_macs,
                    'start-all' : self.start_all,
                    'stop-all' : self.stop_all }

        if len(self.params.command) > 1:
            print "Please only use one command at a time!\n\n"
            parser.print_help()
            sys.exit(1)

        for command in self.params.command:
            if command in actions:
                actions[command]()

    def _print(self, output, verbose=False):
        """ print wrapper so -v and -s can be respected """
        if not self.params.silent:
            if verbose is False:
                print(output)
            elif verbose is True and self.params.verbose > 0:
                print(output)


    def get_macs(self):
        """ This returns the mac addresses  xx:xx:xx,yy:yy:yy aa:aa:aa,bb:bb:bb """
        output=''
        domains=self.conn.listDefinedDomains()

        for domain in domains:
            if not domain.find(self.params.prefix) == -1:
               _xml = objectify.fromstring(self.conn.lookupByName(domain).XMLDesc(0))

               output += "%s" % _xml.devices.interface[0].mac.attrib.get("address")
               try:
                  output += ",%s " % _xml.devices.interface[1].mac.attrib.get("address")
               except IndexError:
                  output += " "


        print '%s' % output.strip(' ')


    def destroy_bridge(self):
        """ This destroys the bridge """
        if not self.is_already_bridge():
            self._print('%s network not found' % self.params.bridge)
            return

        network = self.conn.networkLookupByName(self.params.bridge)
        if network.isActive():
            network.destroy()
        network.undefine()

        self._print("removing dnsmasq exclusion file", True)
        try:
            os.remove('/etc/dnsmasq.d/%s' % self.params.bridge)
        except:
            self._print("dnsmasq exclusion missing.", True)

        self._print('bridge %s destroyed' % self.params.bridge )

    def is_already_bridge(self):
        """ returns t/f if a bridge exists or not """
        #listNetworks = list the active networks
        #listDefinedNetworks = list the inactive networks
        all_networks = self.conn.listNetworks() + \
                       self.conn.listDefinedNetworks()
        return self.params.bridge in all_networks

    def build_bridge_xml(self):
        """ """
        root = etree.Element('network')
        name_el = etree.SubElement(root, 'name')
        name_el.text = self.params.bridge

        stp = "on" if len(self.params.bridge_port) > 1 else "off"
        bridge_el = etree.SubElement(root, 'bridge',
                                     name=self.params.bridge,
                                     stp=stp)

        if self.params.bridge_ip and self.params.bridge_ip.lower() != 'none':
            etree.SubElement(root, 'ip', address=self.params.bridge_ip)

        for p in self.params.bridge_port:
            etree.SubElement(root, 'forward', mode='route', dev=p)

        return etree.tostring(root)

    def create_bridge(self):
        """ this creates a bridge """

        if self.is_already_bridge():
            print('bridge already exists')
            return

        self._print("  Creating a new bridge interface %s." %
            self.params.bridge, verbose=True)

        self.conn.networkDefineXML(self.build_bridge_xml())

        self._print("   Writing dnsmasq.d exclusion file.", verbose=True)

        with file('/etc/dnsmasq.d/%(bridge)s' % dict(bridge=self.params.bridge), 'wb') as outf:
            outf.write('bind-interfaces\nexcept-interface=%(bridge)s\n' %
                dict(bridge=self.params.bridge))

        self._print ("    Wrote dnsmasq.d exclusion file /etc/dnsmasq.d/%s." %
            self.params.bridge, verbose=True)

        self._print('bring bridge online')
        network = self.conn.networkLookupByName(self.params.bridge)
        network.setAutostart(True)
        network.create()

        #idx=self.params.bridge_ip.rindex('.')
        #net=self.params.bridge_ip[0:idx] + ".0"
        #self._print('Adding route for bridge network')
        #call('route add -net %s netmask 255.255.255.0 %s' %
        #      (net, self.params.bridge),
        #      shell=True)

    def load_xml(self, name, image):
        """Loads the xml file and evals it with the right settings"""
        self._print('load_xml called')

        if not self.xml_template:
            template_xml = open(self.params.template_xml, 'r').read()

        return template_xml % dict( engine=self.params.engine,
                                    arch=self.params.arch,
                                    bridge=self.params.bridge,
                                    name=name,
                                    max_mem=self.params.max_mem,
                                    cpus=self.params.cpus,
                                    image=image )


    def destroy_vms(self):
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
        call(cmd, shell=True)


    def create_vms(self):
        """ creates the first vm """
        self._print('create called')

        if not os.path.isdir(self.params.image_path):
                os.makedirs(self.params.image_path)

        for i in range(self.params.vms):
            name = "%s%s" % (self.params.prefix , str(i))
            image = "%s%s.img" % (self.params.image_path, name)
            call("sudo rm -f %s" % image, shell=True)
            cmd = "kvm-img create -f raw %s %s" % (image, self.params.disk_size)
            call(cmd, shell=True)

            self.conn.defineXML(self.load_xml(name,image))

        self._print('Fixing permissions and ownership', verbose=True)
        cmd = 'chmod 644 %s*' % self.params.image_path
        return_code = call(cmd, shell=True)

        cmd = 'sudo chown libvirt-qemu %s*' % self.params.image_path
        call(cmd, shell=True)

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


