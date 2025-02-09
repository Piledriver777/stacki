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

import string
import stack.commands
import stack.gen
import stack.redhat.gen


class Implementation(stack.commands.list.host.profile.implementation):

        def generator(self):
                return stack.redhat.gen.Generator()

        def chapter(self, generator, profile):

                if generator.getProfileType() == 'native':
                        profile.append('<chapter name="kickstart">')
                        for section in [ 'main',
                                         'packages',
                                         'pre',
                                         'post',
                                         'boot' ]:
                                profile.append('\t<section name="%s">' % section)
                                for line in generator.generate(section):
                                        profile.append(line)
                                profile.append('\t</section>')
                        profile.append('</chapter>')

                elif generator.getProfileType() == 'shell':
                        profile.append('<chapter name="bash">')
                        profile.append('#! /bin/bash')
                        for section in [ 'packages',
                                         'post',
					 'boot' ]:
                                profile.append('\t<section name="%s">' % section)
                                for line in generator.generate(section):
                                        profile.append(line)
                                profile.append('\t</section>')
                        profile.append('</chapter>')


