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
#
# @Copyright@
#  				Rocks(r)
#  		         www.rocksclusters.org
#  		         version 5.4 (Maverick)
#  
# Copyright (c) 2000 - 2010 The Regents of the University of California.
# All rights reserved.	
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
# 	"This product includes software developed by the Rocks(r)
# 	Cluster Group at the San Diego Supercomputer Center at the
# 	University of California, San Diego and its contributors."
# 
# 4. Except as permitted for the purposes of acknowledgment in paragraph 3,
# neither the name or logo of this software nor the names of its
# authors may be used to endorse or promote products derived from this
# software without specific prior written permission.  The name of the
# software includes the following terms, and any derivatives thereof:
# "Rocks", "Rocks Clusters", and "Avalanche Installer".  For licensing of 
# the associated name, interested parties should contact Technology 
# Transfer & Intellectual Property Services, University of California, 
# San Diego, 9500 Gilman Drive, Mail Code 0910, La Jolla, CA 92093-0910, 
# Ph: (858) 534-5815, FAX: (858) 534-7345, E-MAIL:invent@ucsd.edu
#  
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS''
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS
# BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
# BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
# OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN
# IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# @Copyright@

from __future__ import print_function
import sys
import string
import stack.commands
import os
import subprocess
from stack.exception import *

class Command(stack.commands.set.host.command):
	"""
	Set a bootaction for a host. A hosts action can be set to 'install' 
	or to 'os' (also, 'run' is a synonym for 'os').

	<arg type='string' name='host' repeat='1'>
	One or more host names.
	</arg>

	<param type='string' name='action'>
	The label name for the bootaction. This must be one of: 'os',
	'install', or 'run'.

	If no action is supplied, then only the configuration file for the
	list of hosts will be rewritten.
	</param>
		
	<example cmd='set host boot compute-0-0 action=os'>
	On the next boot, compute-0-0 will boot the profile based on its
	"run action". To see the node's "run action", execute:
	"rocks list host compute-0-0" and examine the value in the
	"RUNACTION" column.
	</example>
	"""

	def updateBoot(self, host, action):
		#
		# is there already an entry in the boot table
		#
		nrows = self.db.execute("""select b.id from boot b, nodes n
			where n.name = '%s' and n.id = b.node""" % host)

		if nrows < 1:
			#
			# insert a new row
			#
			self.db.execute("""insert into boot (node, action)
				values((select id from nodes where name = '%s'),
				"%s") """ % (host, action))
		else:
			#
			# update an existing row
			#
			bootid, = self.db.fetchone()

			self.db.execute("""update boot set action = "%s"
				where id = %s """ % (action, bootid))
		return

        
	def run(self, params, args):
		(action,) = self.fillParams([('action', )])
		
		if not len(args):
                	raise ArgRequired(self, 'host')

		if action not in [ 'os', 'run', 'install', None ]:
                	raise ParamValue(self, 'action', '"os", "run" or "install"')

                hosts      = self.getHostnames(args)
		for host in hosts:
			if action:
				self.updateBoot(host, action)
			output = self.command('report.host.pxefile',[host, 'action=%s' % action])
			p = subprocess.Popen(['/opt/stack/bin/stack','report','script'],
				stdin = subprocess.PIPE,
				stdout= subprocess.PIPE,
				stderr= subprocess.PIPE)
			o, e = p.communicate(output)
			psh = subprocess.Popen(['/bin/sh'],
				stdin = subprocess.PIPE,
				stdout= subprocess.PIPE,
				stderr= subprocess.PIPE)
			out, err = psh.communicate(o)
