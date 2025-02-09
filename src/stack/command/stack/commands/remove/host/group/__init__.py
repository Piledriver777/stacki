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

class Command(stack.commands.remove.host.command):
	"""
	Removes a group from or more hosts.

	<arg type='string' name='host' repeat='1'>
	One or more host names.
	</arg>

	<param type='string' name='group' optional='0'>
        Group for the host.
	</param>

	<example cmd='remove host group backend-0-0 group=test'>
	Removes host backend-0-0 from the test group.
	</example>
	"""

	def run(self, params, args):

                if len(args) == 0:
                        raise ArgRequired(self, 'host')
        
                hosts = self.getHostnames(args)
                
		(group, ) = self.fillParams([
                        ('group', None, True)
                        ])
		
                if not hosts:
                        raise ArgRequired(self, 'host')
		if not len(hosts) == 1:
                        raise ArgUnique(self, 'host')

                membership = {}
                for row in self.call('list.host.group'):
                        membership[row['host']] = row['groups']
                for host in hosts:
                        if group not in membership[host]:
                                raise CommandError(self, '%s is not a member of %s' % (host, group))

                for host in hosts:
                        self.db.execute(
                                """
                                delete from memberships 
                                where
                                nodeid = (select id from nodes where name='%s')
                                and
                                groupid = (select id from groups where name='%s')
                                """ % (host, group))

