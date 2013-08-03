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

import paramiko
import argparse
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
    hostname = "127.0.0.1"
    password = ""
    keyfilename='C:\Users\krelle\Documents\ssh_keys\id_rsa_hp_key.priv'
    username = "krelle"
    port = 22

    def _format_mac(self, rawmac):
        """ Returns rawmac with colon every two chars. """ 
        return ':'.join(rawmac[i:i+2] for i in xrange(0, len(rawmac), 2))


    def _get_vm_list(self):
        """ Return a list of vms. """
        # Filter out vms we dont want to delete.
        exclude_list = ['"Dib-Raring"']
        return_list=[]
        stdin, stdout, stderr = self.conn.exec_command("VBoxManage list vms")
        raw_list = stdout.read().split()
        for vm_name in raw_list:
            if vm_name[0] == '{':
                # for our needs skip uuid
                continue
            found_in_exclude = False
            for exclude_vm in exclude_list:
                if vm_name in exclude_vm:
                    found_in_exclude = True
                    break
            if found_in_exclude:
                continue
            return_list.append(vm_name)
        return return_list


    def __call__(self, parser, params, values, option_string=None, **kwargs):
        """Triggered by -c command line argument """
        self.params = params
        setattr(self.params, self.dest, values)

        self._print(self.params, verbose=True)

        self.conn=paramiko.SSHClient()
        self.conn.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.conn.connect(self.hostname, port=self.port, username=self.username, password=self.password, key_filename=self.keyfilename)
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
        vm_list = self._get_vm_list()

        for vm in vm_list:
            VBoxCommand = "VBoxManage showvminfo %s --machinereadable | grep macaddress" % vm
            stdin, stdout, stderr = self.conn.exec_command(VBoxCommand)
            macaddList= stdout.read().split()
            for macaddress in macaddList:
                tmp, rawmac = macaddress.split('=')
                mac = rawmac.replace('"','')
                finishedMac = self._format_mac(mac)
                if output:
                    output += ","
                output += "%s" % finishedMac
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

    def get_emulator(self):
        """
        Return the right emulator. RedHat and Debian based systems have
        different executable names.
        """
        if os.path.exists("/usr/bin/kvm"): # Debian
            return "/usr/bin/kvm"
        elif os.path.exists("/usr/bin/qemu-kvm"): # Redhat
            return "/usr/bin/qemu-kvm"
        else:
            self._print("ERROR: Emulator not found. You need to have either "
                        "kvm or qemu-kvm installed before continue.")
            sys.exit(1)


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
                                    emulator=self.get_emulator(),
                                    image=image )


    def destroy_vms(self):
        """ clears out vms """
        self._print('Deleting VMs')

        vm_list = self._get_vm_list()

        for vm in vm_list:
            self._print("Found %s, deleting it" % vm)
            cmd = "VBoxManage unregistervm %s --delete" % vm
            print "Running: %s" % cmd
            stdin, stdout, stderr = self.conn.exec_command(cmd)
            print "Got: %s" % stdout.read()

        #self._print("Deleting disk images from %s" % self.params.image_path)
        #cmd = "rm -rf %s*" % self.params.image_path
        #call(cmd, shell=True)

    def user_exist(self, user):
        # for vbox we using ssh. so we know the user is there
        return True
        
    def create_vms(self):
        """ creates the first vm """
        self._print('create called')

        if not os.path.isdir(self.params.image_path):
                os.makedirs(self.params.image_path)

        for i in range(self.params.vms):
            name = "%s%s" % (self.params.prefix , str(i))
            image = "%s%s.vdi" % (self.params.image_path, name)

            print "Delete VBox vm: %s with disk: %s if it exists" % (name, image)
            stdin, stdout, stderr = self.conn.exec_command("VBoxManage unregistervm %s --delete" % name)
            cmd = "VBoxManage createhd --format VDI --filename %s --size %s" % (image, self.params.disk_size)
            print "Running: %s" % cmd
            stdin, stdout, stderr = self.conn.exec_command(cmd)
            print "Got: %s" % stdout.read()
            # now create the vm
            cmd = "VBoxManage createhd --format VDI --filename %s --size %s" % (image, self.params.disk_size)
            print "Running: %s" % cmd
            stdin, stdout, stderr = self.conn.exec_command(cmd)
            print "Got: %s" % stdout.read()

            cmd = "VBoxManage createvm "\
                "--ostype Ubuntu_64 " \
                "--register " \
                "--name %s" % name
            print "Running: %s" % cmd
            stdin, stdout, stderr = self.conn.exec_command(cmd)
            print "Got: %s" % stdout.read()

            cmd = "VBoxManage storagectl %s " \
                "--name SATA " \
                "--add sata " \
                "--controller IntelAHCI" % name
            print "Running: %s" % cmd
            stdin, stdout, stderr = self.conn.exec_command(cmd)
            print "Got: %s" % stdout.read()

            cmd = "VBoxManage storageattach %s " \
                "--storagectl SATA " \
                "--port 0 " \
                "--device 0 " \
                "--type hdd " \
                "--medium %s" % (name, image)
            print "Running: %s" % cmd
            stdin, stdout, stderr = self.conn.exec_command(cmd)
            print "Got: %s" % stdout.read()

            cmd = "VBoxManage modifyvm %s " \
                "--boot1 net " \
                "--boot2 none " \
                "--boot3 none " \
                "--boot4 none " \
                "--memory 1024" \
                "--cpus 1 " \
                "--intnet1 pxelan" \
                "--nic1 intnet " \
                "--macaddress1 auto " % (name)
            print "Running: %s" % cmd
            stdin, stdout, stderr = self.conn.exec_command(cmd)
            print "Got: %s" % stdout.read()
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
