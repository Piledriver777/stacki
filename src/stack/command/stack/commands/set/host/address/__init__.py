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
#
# $Log:$
#

from __future__ import print_function
import os.path
import getpass
import crypt
import stack.commands
from stack.exception import *


class Command(stack.commands.HostArgumentProcessor, stack.commands.set.command):
	"""
	Change the networking info for a frontend.
	
	<arg type='string' name='host' optional='0'>
	The name of the frontend.
	</arg>

	<param type='string' name='ip'>
	The new IP address.
	</param>

	<param type='string' name='netmask'>
	The new netmask (e.g., 255.255.0.0).
	</param>

	<param type='string' name='shortname'>
	The new short name. This is the first part of the FQDN. For
	example, if the FQDN is a.yoda.com, then the short name is 'a'.
	</param>

	<param type='string' name='domain'>
	The new domain name. This is the last part of the FQDN. For
	example, if the FQDN is a.yoda.com, then the domain name is
	'yoda.com'.
	</param>

	<param type='string' name='gateway'>
	The new public gateway.
	</param>

	<param type='string' name='dns'>
	The new public DNS. For example, '8.8.8.8'.
	</param>

	<example cmd='set host address localhost ip=1.2.3.4'>
	Change the frontend's IP address to 1.2.3.4.
	</example>
	"""

	def readpassword(self):
		import pwd

		#
		# read the old password
		#
		p = pwd.getpwuid(os.geteuid())

		if p[0] != 'root':
			return ''

		if p[1] in [ 'x', '*' ]:
			#
			# need to read /etc/shadow (python v2.6 has the
			# 'spwd' which does that for you).
			#
			file = open('/etc/shadow', 'r')
	
			for line in file.readlines():
				l = line.split(':')
				if len(l) > 1 and l[0] == 'root':
					oldpw = l[1]
					break

			file.close()
		else:
			oldpw = p[1]
			
		return oldpw


	def run(self, params, args):
		(ip, netmask, shortname, domainname, gateway, dns) = self.fillParams([
                        ('ip', None),
			('netmask', None),
                        ('shortname', None),
			('domain', None),
                        ('gateway', None),
			('dns', None)
                        ])

		if len(params) == 0:
                        raise CommandError(self, 'no parameters specified')

		if not ip:
			ip = self.db.getHostAttr('localhost',
				'Kickstart_PublicAddress')
		if not netmask:
			netmask = self.db.getHostAttr('localhost',
				'Kickstart_PublicNetmask')
		if not shortname:
			shortname = self.db.getHostAttr('localhost',
				'Kickstart_PrivateHostname')
		if not domainname:
			domainname = self.db.getHostAttr('localhost',
				'Kickstart_PublicDNSDomain')
		if not gateway:
			gateway = self.db.getHostAttr('localhost',
				'Kickstart_PublicGateway')
		if not dns:
			dns = self.db.getHostAttr('localhost',
				'Kickstart_PublicDNSServers')

		ip = ip.strip()
		netmask = netmask.strip()
		shortname = shortname.strip()
		domainname = domainname.strip()
		gateway = gateway.strip()
		dns = dns.strip()

		hosts = self.getHostnames(args)

		if len(hosts) != 1:
                        raise ArgUnique(self, 'host')

		host = hosts[0]

		if host != self.db.getHostname('localhost'):
                        raise CommandError(self, 'must supply the current name of this frontend')

		oldhost = self.db.getHostAttr('localhost',
			'Kickstart_PrivateHostname')
		oldip = self.db.getHostAttr('localhost',
			'Kickstart_PublicAddress')

		oldhost = oldhost.strip()
		oldip = oldip.strip()

		#
		# calculate some networking variables
		#
		cidr = os.popen("/bin/ipcalc -p %s %s" % (ip, netmask) +
			" | awk -F =  '{print $2}'").read()
		broadcast = os.popen("/bin/ipcalc -b %s %s" % (ip, netmask) +
			" | awk -F =  '{print $2}'").read()
		network = os.popen("/bin/ipcalc -n %s %s" % (ip, netmask) +
			" | awk -F =  '{print $2}'").read()

		cidr = cidr.strip()
		broadcast = broadcast.strip()
		network = network.strip()

		#
		# inform the user what they are about to do
		#
		print('')
		print('You are about to apply new networking values' + \
			' to your frontend:')

		if oldip != ip:
			print('')
			print('\tnew IP: %s' % (ip))
			print('\told IP: %s' % (oldip))

		if netmask != self.db.getHostAttr('localhost',
				'Kickstart_PublicNetmask'):
			print('')
			print('\tnew netmask: %s' % (netmask))
			print('\told netmask: %s' % (self.db.getHostAttr(
				'localhost', 'Kickstart_PublicNetmask')))

		if gateway != self.db.getHostAttr('localhost',
				'Kickstart_PublicGateway'):
			print('')
			print('\tnew gateway: %s' % (gateway))
			print('\told gateway: %s' % (self.db.getHostAttr(
				'localhost', 'Kickstart_PublicGateway')))

		if dns != self.db.getHostAttr('localhost',
				'Kickstart_PublicDNSServers'):
			print('')
			print('\tnew dns: %s' % (dns))
			print('\told dns: %s' % (self.db.getHostAttr(
				'localhost', 'Kickstart_PublicDNSServers')))

		if shortname != self.db.getHostAttr('localhost',
				'Kickstart_PrivateHostname'):
			print('')
			print('\tnew shortname: %s' % (shortname))
			print('\told shortname: %s' % (self.db.getHostAttr(
				'localhost', 'Kickstart_PrivateHostname')))

		if domainname != self.db.getHostAttr('localhost',
				'Kickstart_PublicDNSDomain'):
			print('')
			print('\tnew domain: %s' % (domainname))
			print('\told domain: %s' % (self.db.getHostAttr(
				'localhost', 'Kickstart_PublicDNSDomain')))

		print('')
		print('If this looks correct, then enter the current UNIX root')

		#
		# get the root password in order to access the database
		#
		clear_password = getpass.getpass('password: ')

		#
		# check if the old password matches
		#
		password = self.readpassword()

		if crypt.crypt(clear_password, password) != password:
                        raise CommandError(self, 'The current password you entered does not match the stored password')

		#
		# update the name in the nodes and networks tables first
		#
		print('Updating host name and network interface values ' + \
			'in the database')

		self.command('set.host.name', [ oldhost, shortname ])

		self.db.execute("""update nodes n, networks net 
			set net.name = '%s' where n.name = '%s' and
			n.id = net.node and ip is not NULL"""
			% (shortname, shortname))

		self.db.execute("""update nodes n, networks net, subnets s
			set net.ip = '%s' where n.name = '%s' and
			n.id = net.node and s.name = 'public' and
			net.subnet = s.id""" % (ip, shortname))

		os.system('/bin/hostname %s.%s' % (shortname, domainname))
		os.system('/bin/domainname %s' % (domainname))

		#
		# massage /etc/hosts
		#
		oldfqdn = '%s.%s' % (oldhost, olddomain)
		newfqdn = '%s.%s' % (shortname, domainname)

		makealias = 0
		if oldip == ip and oldfqdn != newfqdn:
			makealias = 1

		newhosts = []
		file = open('/etc/hosts', 'r')
		for line in file.readlines():
			if len(line) == 0:
				continue

			l = line.split()
			if len(l) > 1:
				if oldfqdn in l[1:]:
					if makealias:
						line = '%s %s\n' % \
							(line[:-1], newfqdn)
					else:
						line = '%s\t%s.%s\n' % (ip,
							shortname, domainname)

			newhosts.append(line)

		file.close()

		file = open('/etc/hosts', 'w')
		for line in newhosts:
			file.write('%s' % line)
		file.close()

		#
		# set all the attributes to the new values. then the plugins
		# can simply access the attributes to get the updated values
		#
		print('Updating global attributes')

		self.command('set.attr', [ 'Kickstart_PublicHostname',
			'%s.%s' % (shortname, domainname) ])
		self.command('set.attr', [ 'Kickstart_PrivateHostname',
			shortname ])
		self.command('set.attr', [ 'Kickstart_PublicDNSDomain',
			domainname ])
		self.command('set.attr', [ 'Kickstart_PublicAddress',
			ip ])
		self.command('set.attr', [ 'Kickstart_PublicNetmask',
			netmask ])
		self.command('set.attr', [ 'Kickstart_PublicNetwork',
			network ])
		self.command('set.attr', [ 'Kickstart_PublicBroadcast',
			broadcast ])
		self.command('set.attr', [ 'Kickstart_PublicNetmaskCIDR',
			cidr ])
		self.command('set.attr', [ 'Kickstart_PublicGateway',
			gateway ])
		self.command('set.attr', [ 'Kickstart_PublicDNSServers',
			dns ])

		#
		# now run the plugins
		#
		self.runPlugins( [ oldhost, oldip, clear_password ] )

		self.command('sync.config')

		#
		# steal code from 'rocks sync host network' to get the
		# network configuration set. the reason why we don't call
		# 'rocks sync host network' is because it uses ssh to try to
		# apply the changes, and since we are changing the networking,
		# there are times when we will not be able to consistently
		# ssh to this host (because the network name is in flux).
		#
		attrs = self.db.getHostAttrs('localhost')

		cmd = '/opt/stack/bin/stack report host interface localhost |'
		cmd += '/opt/stack/bin/stack report script '
		cmd += 'attrs="%s" | bash > /dev/null 2>&1' % attrs
		os.system(cmd)

		cmd = '/opt/stack/bin/stack report host network localhost |'
		cmd += '/opt/stack/bin/stack report script '
		cmd += 'attrs="%s" | bash > /dev/null 2>&1' % attrs
		os.system(cmd)

		cmd = '/opt/stack/bin/stack report host route localhost '
		cmd += '> /etc/sysconfig/static-routes'
		os.system(cmd)

		#
		# now let's run the real 'rocks sync host network'
		#
		self.command('sync.host.network', [ 'localhost', 'restart=no' ])

		print('')
		print('Update complete')
		print('')
		print('You must reboot your frontend now. When ' + \
			'the frontend reboots, ')
		print('remember to reinstall the compute nodes.')
		print('')
