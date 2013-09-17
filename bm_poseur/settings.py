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

import os

class settings(object):
    """Constants .. don't change this file unless you want to perm change the defaults"""
    # how many do you want to create (should be command line arg)
    VMS = 1
    ARCH = "x86_64"
    ENGINE = "kvm"
    MAX_MEM = "524000"
    BOOTSTRAP_IMAGE = "/opt/stack/data/images/bootstrap.qcow2"
    CPUS = "1"
    BRIDGE = "br99"
    BRIDGE_IP = '192.0.2.1'
    
    QEMU = "qemu:///system"
    PREFIX = 'baremetal_'
    IMAGE_PATH = '/opt/stack/data/bm_poseur/'
    DISK_SIZE = "20G"
    START_DELAY = 2
    TEMPLATE_XML = "%s/template.xml" % os.path.dirname(os.path.abspath(__file__))

