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

from __future__ import print_function
import re
import sys
import stack.csv
import stack.commands
from stack.exception import *

class Implementation(stack.commands.ApplianceArgumentProcessor,
	stack.commands.HostArgumentProcessor, stack.commands.Implementation):	

	"""
	Create a dictionary of attributes based on comma-separated formatted
	file.
	"""

	def run(self, args):
		filename, = args

		reader = stack.csv.reader(open(filename, 'rU'))

		# Skip all header line until col[0] == 'target'

		while True:
			header = reader.next()
			if len(header):
				target = header[0].lower()
				if target == 'target':
					break

		# Fix the header to be lowercase and strip out any
		# leading or trailing whitespace.

		for i in range(0, len(header)):
			header[i] = header[i].lower()


		default = {}

		for attr in header:
			self.owner.checkAttr(attr)

		reserved = self.getApplianceNames()
		reserved.append('global')
		reserved.append('default')

		for row in reader:

                        target = None
			attrs = {}
			for i in range(0, len(row)):
				field = row[i]
				self.owner.checkValue(field)
				if header[i] == 'target':
					target = field
				else:
					attrs[header[i]] = field

			if target == 'default':
				default = attrs
			else:
				for key in default.keys():
					if not attrs[key]:
						attrs[key] = default[key]

			if target not in reserved:
				host = self.db.getHostname(target)
				if not host:
					raise CommandError(self.owner, 'target "%s" is not an known appliance or host name' % host)

			if target not in self.owner.attrs.keys():
				self.owner.attrs[target] = {}

			self.owner.attrs[target].update(attrs)

		# If there is a global environment specified make
                # sure each host is in that environment.
                
		try:
			env = self.owner.attrs['global']['environment']
		except:
			env = None
		if env:
                        self.owner.call('set.host.environment',
                                [ target, 'environment=%s' % env ])

