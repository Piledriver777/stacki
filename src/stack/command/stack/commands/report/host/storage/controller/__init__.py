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

from __future__ import print_function
import stack.commands
from stack.exception import *

class Command(stack.commands.HostArgumentProcessor,
	stack.commands.report.command):
	"""
	Output the storage controller configuration for a specific host

	<arg type='string' name='host'>
	One host name.
	</arg>

	<example cmd='report host storage controller compute-0-0'>
	Output the storage controller configuration for compute-0-0.
	</example>
	"""

	def run(self, params, args):
		hosts = self.getHostnames(args)

		if len(hosts) != 1:
                        raise ArgUnique(self, 'host')

		self.beginOutput()

		host = hosts[0]

		#
		# first see if there is a storage controller configuration for
		# this specific host
		#
		output = self.call('list.storage.controller', [ host ])
		if output:
			self.addOutput('', '%s' % output)
			self.endOutput(padChar = '')
			return

		# 
		# now check at the appliance level
		# 
		appliance = self.db.getHostAttr(host, 'appliance')

		output = self.call('list.storage.controller', [ appliance ])
		if output:
			self.addOutput('', '%s' % output)
			self.endOutput(padChar = '')
			return

		#
		# finally check the global level
		#
		output = self.call('list.storage.controller')
		if output:
			self.addOutput('', '%s' % output)
			self.endOutput(padChar = '')
			return

		#
		# if we made it here, there is no storage controller
		# configuration for this host
		#
		output = []
		self.addOutput('', '%s' % output)
		self.endOutput(padChar = '')
