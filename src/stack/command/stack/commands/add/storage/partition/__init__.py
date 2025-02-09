# @SI_Copyright@
#                               stacki.com
#                                  v3.3
# 
#      Copyright (c) 2006 - 2016 StackIQ Inc. All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#  
# 1. Redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer.
#  
# 2. Redistributions in binary form must reproduce the above copyright
# notice unmodified and in its entirety, this list of conditions and the
# following disclaimer in the documentation and/or other materials provided 
# with the distribution.
#  
# 3. All advertising and press materials, printed or electronic, mentioning
# features or use of this software must display the following acknowledgement: 
# 
# 	 "This product includes software developed by StackIQ" 
#  
# 4. Except as permitted for the purposes of acknowledgment in paragraph 3,
# neither the name or logo of this software nor the names of its
# authors may be used to endorse or promote products derived from this
# software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY STACKIQ AND CONTRIBUTORS ``AS IS''
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL STACKIQ OR CONTRIBUTORS
# BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
# BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
# OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN
# IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# @SI_Copyright@

import stack.commands
from stack.exception import *

class Command(stack.commands.HostArgumentProcessor,
		stack.commands.ApplianceArgumentProcessor,
		stack.commands.add.command):
	"""
	Add a partition configuration to the database.

        <arg type='string' name='scope'>
	Zero or one argument. The argument is the scope: a valid os (e.g.,
	'redhat'), a valid appliance (e.g., 'compute') or a valid host
	(e.g., 'compute-0-0). No argument means the scope is 'global'.
        </arg>

	<param type='string' name='device' optional='1'>
	Disk device on which we are creating partitions
	</param>

	<param type='string' name='mountpoint' optional='1'>
	Mountpoint to create
	</param>

        <param type='int' name='size' optional='1'>
	Size of the partition.
        </param>

	<param type='string' name='type' optional='1'>
	Type of partition E.g: ext4, ext3, xfs, raid, etc.
	</param>

	<param type='string' name='options' optional='0'>
	Options that need to be supplied while adding partitions.
	</param>

	<param type='string' name='partid' optional='1'>
	The relative partition id for this partition. Partitions will be
	created in ascending partition id order.
	</param>
	
	<example cmd='add storage partition compute-0-0 device=sda mountpoint=/var
		size=50 type=ext4'>
	Creates a ext4 partition on device sda with mountpoints /var.
	</example>

	<example cmd='add storage partition compute-0-2 device=sdc mountpoint=pv.01
		 size=0 type=lvm'>
	Creates a physical volume named pv.01 for lvm.
	</example>

	<example cmd='add storage partition compute-0-2 mountpoint=volgrp01 device=pv.01 pv.02 pv.03
		size=32768 type=volgroup'>
	Creates a volume group from 3 physical volumes i.e. pv.01, pv.02, pv.03. All these 3
	physical volumes need to be created with the previous example. PV's need to be space
	separated.
	</example>
	<example cmd='add storage partition compute-0-2 device=volgrp01 mountpoint=/banktools
		size=8192 type=xfs options=--name=banktools'>
	Created an xfs lvm partition of size 8192 on volgrp01. volgrp01 needs to be created
	with the previous example.
	</example>
	"""

	#
	# Checks if partition config already exists in DB for a device and 
	# a mount point.
	#
	def checkIt(self, device, scope, tableid, mountpt):
		self.db.execute("""select Scope, TableID, Mountpoint,
			device, Size, FsType from storage_partition where
			Scope='%s' and TableID=%s and device= '%s'
			and Mountpoint='%s'""" % (scope, tableid, device, mountpt))

		row = self.db.fetchone()

		if row:
			raise CommandError(self, """partition specification for device %s,
				mount point %s already exists in the 
				database""" % (device, mountpt))

	def run(self, params, args):
		scope = None
		oses = []
		appliances = []
		hosts = []

		if len(args) == 0:
			scope = 'global'
		elif len(args) == 1:
			try:
				oses = self.getOSNames(args)
			except:
				oses = []

			try:
				appliances = self.getApplianceNames(args)
			except:
				appliances = []

			try:
				hosts = self.getHostnames(args)
			except:
				hosts = []
		else:
			raise ArgRequired(self, 'scope')

		if not scope:
			if args[0] in oses:
				scope = 'os'
			elif args[0] in appliances:
				scope = 'appliance'
			elif args[0] in hosts:
				scope = 'host'

		if not scope:
			raise ArgValue(self, 'scope', 'valid os, appliance name or host name')

		if scope == 'global':
			name = 'global'
		else:
			name = args[0]

		device, size, fstype, mountpt, options, partid = \
			self.fillParams([
				('device', None, True),
				('size', None), 
				('type', None), 
				('mountpoint', None),
				('options', None),
				('partid', None),
				])

		if not device:
			raise ParamRequired(self, 'device')

		# Validate size
		if size:
			try:
				s = int(size)
			except:
				#
				# If mountpoint is 'swap' then allow
				# 'hibernate', 'recommended' as sizes.
				#
				if mountpt == 'swap' and \
					size not in ['recommended', 'hibernation']:
						raise ParamType(self, 'size', 'integer')
			if s < 0:
				raise ParamValue(self, 'size', '>= 0')

		# Validate partid
		if partid:
			try:
				p = int(partid)
			except:
				partid = None

			if p < 1:
				raise ParamValue(self, 'partid', '>= 0')

			partid = p

		#
		# look up the id in the appropriate 'scope' table
		#
		tableid = None
		if scope == 'global':
			tableid = -1
		elif scope == 'appliance':
			self.db.execute("""select id from appliances where
				name = '%s' """ % name)
			tableid, = self.db.fetchone()
		elif scope == 'host':
			self.db.execute("""select id from nodes where
				name = '%s' """ % name)
			tableid, = self.db.fetchone()

		#
		# make sure the specification for mountpt doesn't already exist
		#
		if mountpt:
			self.checkIt(device, scope, tableid, mountpt)

		if not options:
			options = ""
		
		#
		# now add the specifications to the database
		#
		sqlvars = "Scope, TableID, device, Mountpoint, Size, FsType, Options"
		sqldata = "'%s', %s, '%s', '%s', %s, '%s', '%s'" % \
			(scope, tableid, device, mountpt, size, fstype, options)

		if partid:
			sqlvars += ", PartID"
			sqldata += ", %s" % partid

		self.db.execute("""insert into storage_partition
			(%s) values (%s) """ % (sqlvars, sqldata))
