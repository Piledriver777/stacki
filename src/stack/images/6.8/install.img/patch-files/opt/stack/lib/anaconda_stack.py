#!/usr/bin/python
#
# anaconda: The Red Hat Linux Installation program
#
# Copyright (C) 1999, 2000, 2001, 2002, 2003, 2004, 2005, 2006, 2007
# Red Hat, Inc.  All rights reserved.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Author(s): Brent Fox <bfox@redhat.com>
#            Mike Fulbright <msf@redhat.com>
#            Jakub Jelinek <jakub@redhat.com>
#            Jeremy Katz <katzj@redhat.com>
#            Chris Lumens <clumens@redhat.com>
#            Paul Nasrat <pnasrat@redhat.com>
#            Erik Troan <ewt@rpath.com>
#            Matt Wilson <msw@rpath.com>
#

# This toplevel file is a little messy at the moment...

from __future__ import print_function
import sys, os, re, time, subprocess, atexit
from optparse import OptionParser
from tempfile import mkstemp

# keep up with process ID of the window manager if we start it
wm_pid = None
xserver_pid = None

def return_tty(fd, pgrp_id):
    try:
        os.tcsetpgrp(fd, pgrp_id)
    except OSError as oserr:
        #fails on s390 and s390x where we don't need it
        pass

# Make sure messages sent through python's warnings module get logged.
def AnacondaShowWarning(message, category, filename, lineno, file=sys.stderr, line=None):
    log.warning("%s" % warnings.formatwarning(message, category, filename, lineno, line))

def startMetacityWM():
    childpid = os.fork()
    if not childpid:
        # after this point the method should never return (or throw an exception
        # outside)
        try:
            args = ['--display', ':1',
                    '--sm-disable']
            iutil.execWithRedirect('metacity', args,
                                   stdout='/dev/null', stderr='/dev/null')
        except BaseException as e:
            # catch all possible exceptions
            log.error("Problems running the window manager: %s" % str(e))
            sys.exit(1)

        log.info("The window manager has terminated.")
        sys.exit(0)
    return childpid

def startAuditDaemon():
    childpid = os.fork()
    if not childpid:
        cmd = '/sbin/auditd'
        try:
            os.execl(cmd, cmd)
        except OSError as e:
            log.error("Error running the audit daemon: %s" % str(e))
        sys.exit(0)
    # auditd will turn into a daemon so catch the immediate child pid now:
    os.waitpid(childpid, 0)

# function to handle X startup special issues for anaconda
def doStartupX11Actions():
    global wm_pid # pid of the anaconda fork where the window manager is running

    setupGraphicalLinks()

    # now start up the window manager
    wm_pid = startMetacityWM()
    log.info("Starting window manager, pid %s." % (wm_pid,))

    if wm_pid is not None:
        import xutils

        try:
            xutils.setRootResource('Xcursor.size', '24')
            xutils.setRootResource('Xcursor.theme', 'Bluecurve')
            xutils.setRootResource('Xcursor.theme_core', 'true')

            xutils.setRootResource('Xft.antialias', '1')
            xutils.setRootResource('Xft.hinting', '1')
            xutils.setRootResource('Xft.hintstyle', 'hintslight')
            xutils.setRootResource('Xft.rgba', 'none')
        except:
            sys.stderr.write("X SERVER STARTED, THEN FAILED");
            raise RuntimeError, "X server failed to start"

def set_x_resolution(runres):
    # cant do this if no window manager is running because otherwise when we
    # open and close an X connection in the xutils calls the X server will exit
    # since this is the first X connection (if no window manager is running)
    if runres and opts.display_mode == 'g' and not flags.usevnc and wm_pid :
        try:
            log.info("Setting the screen resolution to: %s.", runres)
            iutil.execWithRedirect("xrandr", 
                                   ["-d", ":1", "-s", runres],
                                   stdout="/dev/tty5", stderr="/dev/tty5")
        except RuntimeError as e:
            log.error("The X resolution not set")
            iutil.execWithRedirect("xrandr",
                                   ["-d", ":1", "-q"],
                                   stdout="/dev/tty5", stderr="/dev/tty5")

def doShutdownX11Actions():
    global wm_pid
    global xserver_pid
    
    if wm_pid is not None:
        try:
            os.kill(wm_pid, 15)
            os.waitpid(wm_pid, 0)
        except:
            pass

    if xserver_pid is not None:
        try:
            os.kill(xserver_pid, 15)
            os.waitpid(xserver_pid, 0)
        except:
            pass

# handle updates of just a single file in a python package
def setupPythonUpdates():
    import glob

    # get the python version.  first of /usr/lib/python*, strip off the
    # first 15 chars
    pyvers = glob.glob("/usr/lib/python*")
    pyver = pyvers[0][15:]
    
    try:
        os.mkdir("/tmp/updates")
    except:
        pass

    for pypkg in ("block", "yum", "rpmUtils", "urlgrabber", "pykickstart", "parted", "meh"):
        # get the libdir.  *sigh*
        if os.access("/usr/lib64/python%s/site-packages/%s" %(pyver, pypkg),
                     os.X_OK):
            libdir = "lib64"
        elif os.access("/usr/lib/python%s/site-packages/%s" %(pyver, pypkg),
                       os.X_OK):
            libdir = "lib"
        else:
            # If the directory doesn't exist, there's nothing to link over.
            # This happens if we forgot to include one of the above packages
            # in the image, for instance.
            continue

        if os.access("/tmp/updates/%s" %(pypkg,), os.X_OK):
            for f in os.listdir("/usr/%s/python%s/site-packages/%s" %(libdir,
                                                                      pyver,
                                                                      pypkg)):
                if os.access("/tmp/updates/%s/%s" %(pypkg, f), os.R_OK):
                    continue
                elif (f.endswith(".pyc") and
                      os.access("/tmp/updates/%s/%s" %(pypkg, f[:-1]),os.R_OK)):
                    # dont copy .pyc files we are replacing with updates
                    continue
                else:
                    os.symlink("/usr/%s/python%s/site-packages/%s/%s" %(libdir,
                                                                        pyver,
                                                                        pypkg,
                                                                        f),
                               "/tmp/updates/%s/%s" %(pypkg, f))


    import glob
    import shutil
    for rule in glob.glob("/tmp/updates/*.rules"):
        target = "/etc/udev/rules.d/" + rule.split('/')[-1]
        shutil.copyfile(rule, target)

def parseOptions():

    op = OptionParser()
    # Interface
    op.add_option("-C", "--cmdline", dest="display_mode", action="store_const", const="c")
    op.add_option("-G", "--graphical", dest="display_mode", action="store_const", const="g")
    op.add_option("-T", "--text", dest="display_mode", action="store_const", const="t")

    # Network
    op.add_option("--noipv4", action="store_true", default=False)
    op.add_option("--noipv6", action="store_true", default=False)
    op.add_option("--proxy")
    op.add_option("--proxyAuth")

    # Method of operation
    op.add_option("--autostep", action="store_true", default=False)
    op.add_option("-d", "--debug", dest="debug", action="store_true", default=False)
    op.add_option("--kickstart", dest="ksfile")
    op.add_option("--rescue", dest="rescue", action="store_true", default=False)
    op.add_option("--targetarch", dest="targetArch", nargs=1, type="string")

    op.add_option("-m", "--method", dest="method", default=None)
    op.add_option("--repo", dest="method", default=None)
    op.add_option("--stage2", dest="stage2", default=None)
    op.add_option("--noverifyssl", action="store_true", default=False)

    op.add_option("--liveinst", action="store_true", default=False)

    # Display
    op.add_option("--headless", dest="isHeadless", action="store_true", default=False)
    op.add_option("--nofb")
    op.add_option("--resolution", dest="runres", default=None)
    op.add_option("--serial", action="store_true", default=False)
    op.add_option("--usefbx", dest="xdriver", action="store_const", const="fbdev")
    op.add_option("--virtpconsole")
    op.add_option("--vnc", action="store_true", default=False)
    op.add_option("--vncconnect")
    op.add_option("--xdriver", dest="xdriver", action="store", type="string", default=None)

    # Language
    op.add_option("--keymap")
    op.add_option("--kbdtype")
    op.add_option("--lang")

    # Obvious
    op.add_option("--loglevel")
    op.add_option("--syslog")

    op.add_option("--noselinux", dest="selinux", action="store_false", default=True)
    op.add_option("--selinux", action="store_true")

    op.add_option("--nompath", dest="mpath", action="store_false", default=True)
    op.add_option("--mpath", action="store_true")

    op.add_option("--nodmraid", dest="dmraid", action="store_false", default=True)
    op.add_option("--dmraid", action="store_true")

    op.add_option("--noibft", dest="ibft", action="store_false", default=True)
    op.add_option("--ibft", action="store_true")
    op.add_option("--noiscsi", dest="iscsi", action="store_false", default=False)
    op.add_option("--iscsi", action="store_true")
    op.add_option("--noeject", action="store_true")

    # Miscellaneous
    op.add_option("--module", action="append", default=[])
    op.add_option("--nomount", dest="rescue_nomount", action="store_true", default=False)
    op.add_option("--updates", dest="updateSrc", action="store", type="string")
    op.add_option("--dogtail", dest="dogtail",   action="store", type="string")
    op.add_option("--dlabel", action="store_true", default=False)

    # Deprecated, unloved, unused
    op.add_option("-r", "--rootPath", dest="unsupportedMode",
                  action="store_const", const="root path")
    op.add_option("-t", "--test", dest="unsupportedMode",
                  action="store_const", const="test")

    return op.parse_args()

def setupPythonPath():
    haveUpdates = False
    for ndx in range(len(sys.path)-1, -1, -1):
        if sys.path[ndx].endswith('updates'):
            haveUpdates = True
            break

    if haveUpdates:
        sys.path.insert(ndx+1, '/usr/lib/anaconda')
        sys.path.insert(ndx+2, '/usr/lib/anaconda/textw')
        sys.path.insert(ndx+3, '/usr/lib/anaconda/iw')
    else:
        sys.path.insert(0, '/usr/lib/anaconda')
        sys.path.insert(1, '/usr/lib/anaconda/textw')
        sys.path.insert(2, '/usr/lib/anaconda/iw')

    sys.path.append('/usr/share/system-config-date')

def setupEnvironment():
    # Silly GNOME stuff
    if os.environ.has_key('HOME') and not os.environ.has_key("XAUTHORITY"):
        os.environ['XAUTHORITY'] = os.environ['HOME'] + '/.Xauthority'
    os.environ['HOME'] = '/tmp'
    os.environ['LC_NUMERIC'] = 'C'
    os.environ["GCONF_GLOBAL_LOCKS"] = "1"

    # In theory, this gets rid of our LVM file descriptor warnings
    os.environ["LVM_SUPPRESS_FD_WARNINGS"] = "1"

    # make sure we have /sbin and /usr/sbin in our path
    os.environ["PATH"] += ":/sbin:/usr/sbin"

    # we can't let the LD_PRELOAD hang around because it will leak into
    # rpm %post and the like.  ick :/
    if os.environ.has_key("LD_PRELOAD"):
        del os.environ["LD_PRELOAD"]

    os.environ["GLADEPATH"] = "/tmp/updates/:/tmp/updates/ui/:ui/:/usr/share/anaconda/ui/:/usr/share/python-meh/"
    os.environ["PIXMAPPATH"] = "/tmp/updates/pixmaps/:/tmp/updates/:/tmp/product/pixmaps/:/tmp/product/:pixmaps/:/usr/share/anaconda/pixmaps/:/usr/share/pixmaps/:/usr/share/anaconda/:/usr/share/python-meh/"

def setupLoggingFromOpts(opts):
    if opts.loglevel and anaconda_log.logLevelMap.has_key(opts.loglevel):
        level = anaconda_log.logLevelMap[opts.loglevel]
        anaconda_log.logger.loglevel = level
        anaconda_log.setHandlersLevel(log, level)
        anaconda_log.setHandlersLevel(storage.storage_log.logger, level)

    if opts.syslog:
        if opts.syslog.find(":") != -1:
            (host, port) = opts.syslog.split(":")
            anaconda_log.logger.addSysLogHandler(log, host, port=int(port))
        else:
            anaconda_log.logger.addSysLogHandler(log, opts.syslog)

def getInstClass():
    from installclass import DefaultInstall
    return DefaultInstall()

# ftp installs pass the password via a file in /tmp so
# ps doesn't show it
def expandFTPMethod(str):
    ret = None

    try:
        filename = str[1:]
        ret = open(filename, "r").readline()
        ret = ret[:len(ret) - 1]
        os.unlink(filename)
        return ret
    except:
        return None

def runVNC():
    global vncS
    vncS.startServer()

    child = os.fork()
    if child == 0:
        for p in ('/tmp/updates/pyrc.py', \
                '/usr/lib/anaconda-runtime/pyrc.py'):
            if os.access(p, os.R_OK|os.X_OK):
                os.environ['PYTHONSTARTUP'] = p
                break

        while True:
            # Not having a virtual terminal or otherwise free console
            # are the only places we /really/ need a shell on tty1,
            # and everywhere else this just gets in the way of pdb.  But we
            # don't want to return, because that'll return try to start X
            # a second time.
            if iutil.isConsoleOnVirtualTerminal() or iutil.isS390():
                    time.sleep(10000)
            else:
                    print(_("Press <enter> for a shell"))
                    sys.stdin.readline()
                    iutil.execConsole()

def within_available_memory(needed_ram):
    # kernel binary code estimate that is
    # not reported in MemTotal by /proc/meminfo:
    epsilon = 32768 # 32 MB
    return needed_ram < (iutil.memInstalled() + epsilon)

def check_memory(opts, display_mode=None):

    if not display_mode:
        display_mode = opts.display_mode

    reason = ''
    needed_ram = isys.MIN_RAM
    if not within_available_memory(needed_ram):
        from snack import SnackScreen, ButtonChoiceWindow
        screen = SnackScreen()
        ButtonChoiceWindow(screen, _('Fatal Error'),
                            _('You do not have enough RAM to install %s '
                              'on this machine%s.\n'
                              '\n'
                              'Press <return> to reboot your system.\n')
                           %(product.productName, reason),
                           buttons = (_("OK"),))
        screen.finish()
        sys.exit(0)

    # override display mode if machine cannot nicely run X
    if display_mode not in ('t', 'c') and not flags.usevnc:
        needed_ram = isys.MIN_GUI_RAM

        if not within_available_memory(needed_ram):
            stdoutLog.warning(_("You do not have enough RAM to use the graphical "
                                "installer.  Starting text mode."))
            opts.display_mode = 't'
            time.sleep(2)

def setupGraphicalLinks():
    for i in ( "imrc", "im_palette.pal", "gtk-2.0", "pango", "fonts",
               "fb.modes"):
        try:
            if os.path.exists("/mnt/runtime/etc/%s" %(i,)):
                os.symlink ("../mnt/runtime/etc/" + i, "/etc/" + i)
        except:
            pass

def handleSshPw(ks):
    import users
    u = users.Users()

    userdata = ks.sshpw.dataList()
    for ud in userdata:
        if u.checkUserExists(ud.username, root="/"):
            u.setUserPassword(username=ud.username, password=ud.password,
                              isCrypted=ud.isCrypted, lock=ud.lock)
        else:
            u.createUser(name=ud.username, password=ud.password,
                         isCrypted=ud.isCrypted, lock=ud.lock,
                         root="/", mkmailspool=False)

    del u

def createSshKey(algorithm, keyfile):
    path = '/etc/ssh/%s' % (keyfile,)
    argv = ['-q','-t',algorithm,'-f',path,'-C','','-N','']
    log.info("running \"%s\"" % (" ".join(['ssh-keygen']+argv),))

    so = "/tmp/ssh-keygen-%s-stdout.log" % (algorithm,)
    se = "/tmp/ssh-keygen-%s-stderr.log" % (algorithm,)
    iutil.execWithRedirect('ssh-keygen', argv, stdout=so, stderr=se)

def fork_orphan():
    """Forks an orphan.
    
    Returns 1 in the parent and 0 in the orphaned child.
    """
    intermediate = os.fork()
    if not intermediate:
        if os.fork():
            # the intermediate child dies
            os._exit(0)
        return 0;
    # the original process waits for the intermediate child
    os.waitpid(intermediate, 0)
    return 1

def startSsh():
    if iutil.isS390():
        return

    if not fork_orphan():
        os.open("/var/log/lastlog", os.O_RDWR | os.O_CREAT, 0o644)
        ssh_keys = {
            'rsa1':'ssh_host_key',
            'rsa':'ssh_host_rsa_key',
            'dsa':'ssh_host_dsa_key',
            }
        for (algorithm, keyfile) in ssh_keys.items():
            createSshKey(algorithm, keyfile)
        args = ["/sbin/sshd", "-f", "/etc/ssh/sshd_config.anaconda"]
        os.execv("/sbin/sshd", args)
        sys.exit(1)

def startDebugger(signum, frame):
    import epdb
    epdb.serve(skip=1)

class Anaconda(object):
    def __init__(self):
        self.intf = None
        self.dir = None
        self.id = None
        self.methodstr = None
        self.stage2 = None
        self.backend = None
        self.rootPath = "/mnt/sysimage"
        self.dispatch = None
        self.isKickstart = False
        self.rescue_mount = True
        self.rescue = False
        self.updateSrc = None
        self.mediaDevice = None
        self.platform = None
        self.canReIPL = False
        self.reIPLMessage = None
        self.proxy = None
        self.proxyUsername = None
        self.proxyPassword = None
        self.clearPartTypeSelection = None      # User's GUI selection
        self.clearPartTypeSystem = None         # System's selection

        # *sigh* we still need to be able to write this out
        self.xdriver = None

    def dumpState(self):
        from meh.dump import ReverseExceptionDump
        from inspect import stack as _stack

        # Skip the frames for dumpState and the signal handler.
        stack = _stack()[2:]
        stack.reverse()
        exn = ReverseExceptionDump((None, None, stack), self.mehConfig)

        (fd, filename) = mkstemp("", "anaconda-tb-", "/tmp")
        fo = os.fdopen(fd, "w")

        exn.write(self, fo)

    def writeXdriver(self, instPath="/"):
        # this should go away at some point, but until it does, we
        # need to keep it around.  it could go into instdata but this
        # isolates it a little more
        if self.xdriver is None:
            return
        if not os.path.isdir("%s/etc/X11" %(instPath,)):
            os.makedirs("%s/etc/X11" %(instPath,), mode=0o755)
        f = open("%s/etc/X11/xorg.conf" %(instPath,), 'w')
        f.write('Section "Device"\n\tIdentifier "Videocard0"\n\tDriver "%s"\nEndSection\n' % self.xdriver)
        f.close()

    def setDispatch(self):
        self.dispatch = dispatch.Dispatcher(self)

    def setInstallInterface(self, display_mode):
        # setup links required by graphical mode if installing and verify display mode
        if display_mode == 'g':
            stdoutLog.info (_("Starting graphical installation."))

            try:
                from gui import InstallInterface
            except Exception, e:
                stdoutLog.error("Exception starting GUI installer: %s" %(e,))
                # if we're not going to really go into GUI mode, we need to get
                # back to vc1 where the text install is going to pop up.
                if not x_already_set:
                    isys.vtActivate (1)
                stdoutLog.warning("GUI installer startup failed, falling back to text mode.")
                display_mode = 't'
                if 'DISPLAY' in os.environ.keys():
                    del os.environ['DISPLAY']
                time.sleep(2)

        if display_mode == 't':
            from text import InstallInterface
            if not os.environ.has_key("LANG"):
                os.environ["LANG"] = "en_US.UTF-8"

        if display_mode == 'c':
            from cmdline import InstallInterface

        self.intf = InstallInterface()

    def setBackend(self, instClass):
        b = instClass.getBackend()
        self.backend = apply(b, (self,))

    def setMethodstr(self, methodstr):
        if methodstr.startswith("cdrom://"):
            (device, tree) = string.split(methodstr[8:], ":", 1)

            if not tree.startswith("/"):
                tree = "/%s" %(tree,)

            if device.startswith("/dev/"):
                device = device[5:]

            self.mediaDevice = device
            self.methodstr = "cdrom://%s" % tree
        else:
            self.methodstr = methodstr

    def requiresNetworkInstall(self):
        fail = False
        numNetDevs = isys.getNetworkDeviceCount()

        if self.methodstr is not None:
            if (self.methodstr.startswith("http") or \
                self.methodstr.startswith("ftp://") or \
                self.methodstr.startswith("nfs:")) and \
               numNetDevs == 0:
                fail = True
        elif self.stage2 is not None:
            if self.stage2.startswith("cdrom://") and \
               not os.path.isdir("/mnt/stage2/Packages") and \
               numNetDevs == 0:
                fail = True

        if fail:
            log.error("network install required, but no network devices available")

        return fail

    @property
    def protected(self):
        import stat

        if os.path.exists("/dev/live") and \
           stat.S_ISBLK(os.stat("/dev/live")[stat.ST_MODE]):
            return [os.readlink("/dev/live")]
        elif self.methodstr and self.methodstr.startswith("hd:"):
            method = self.methodstr[3:]
            return [method.split(":", 3)[0]]
        else:
            return []

if __name__ == "__main__":
    # Register atexit function before anything bad can happen
    # We have to return tty control back to init's process group
    atexit.register(return_tty, sys.stdin.fileno(), os.getpgid(os.getppid()))

    anaconda = Anaconda()

    setupPythonPath()

    # Allow a file to be loaded as early as possible
    try:
        import updates_disk_hook
    except ImportError:
        pass

    # Set up logging as early as possible.
    import logging
    import anaconda_log

    log = logging.getLogger("anaconda")
    stdoutLog = logging.getLogger("anaconda.stdout")

    # pull this in to get product name and versioning
    import product

    # this handles setting up updates for pypackages to minimize the set needed
    setupPythonUpdates()

    import signal, string, isys, iutil, time
    import dispatch
    import warnings
    import vnc
    import users
    import kickstart
    import storage.storage_log
    from flags import flags

    # the following makes me very sad. -- katzj
    # we have a slightly different set of udev rules in the second 
    # stage than the first stage.  why this doesn't get picked up
    # automatically, I don't know.  but we need to trigger so that we
    # have all the information about netdevs that we care about for 
    # NetworkManager in the udev database
    from baseudev import udev_trigger, udev_settle
    udev_trigger("net")
    udev_trigger("block") # trigger the block subsys too while at it
    udev_settle()
    # and for added fun, once doesn't seem to be enough?  so we 
    # do it twice, it works and we scream at the world "OH WHY?"
    udev_trigger("net")
    udev_settle()

    import gettext
    _ = lambda x: gettext.ldgettext("anaconda", x)

    import platform
    anaconda.platform = platform.getPlatform(anaconda)

    if not iutil.isS390() and os.access("/dev/tty3", os.W_OK):
        anaconda_log.logger.addFileHandler ("/dev/tty3", log)

    warnings.showwarning = AnacondaShowWarning

    iutil.setup_translations(gettext)

    # reset python's default SIGINT handler
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    signal.signal(signal.SIGSEGV, isys.handleSegv)

    setupEnvironment()
    # make sure we have /var/log soon, some programs fail to start without it
    iutil.mkdirChain("/var/log")

    pidfile = open("/var/run/anaconda.pid", "w")
    pidfile.write("%s\n" % (os.getpid(),))
    del pidfile
    # add our own additional signal handlers
    signal.signal(signal.SIGHUP, startDebugger)

    # we need to do this really early so we make sure its done before rpm
    # is imported
    iutil.writeRpmPlatform()

    extraModules = []               # XXX: this would be better as a callback
    graphical_failed = 0
    instClass = None                # the install class to use
    vncS = vnc.VncServer()          # The vnc Server object.
    vncS.anaconda = anaconda

    (opts, args) = parseOptions()

    # check memory, just the text mode for now:
    check_memory(opts, 't')

    if opts.unsupportedMode:
        stdoutLog.error("Running anaconda in %s mode is no longer supported." % opts.unsupportedMode)
        sys.exit(0)

    # Now that we've got arguments, do some extra processing.
    instClass = getInstClass()

    setupLoggingFromOpts(opts)

    # Default is to prompt to mount the installed system.
    anaconda.rescue_mount = not opts.rescue_nomount

    if opts.dlabel: #autodetected driverdisc in use
        flags.dlabel = True

    if opts.noipv4:
        flags.useIPv4 = False

    if opts.noipv6:
        flags.useIPv6 = False

    if opts.proxy:
        anaconda.proxy = opts.proxy

        if opts.proxyAuth:
            filename = opts.proxyAuth
            ret = open(filename, "r").readlines()
            os.unlink(filename)

            anaconda.proxyUsername = ret[0].rstrip()
            if len(ret) == 2:
                anaconda.proxyPassword = ret[1].rstrip()

        # Set environmental variables to be used by pre/post scripts
        os.environ["PROXY"] = anaconda.proxy
        os.environ["PROXY_USER"] = anaconda.proxyUsername or ""
        os.environ["PROXY_PASSWORD"] = anaconda.proxyPassword or ""

    if opts.updateSrc:
        anaconda.updateSrc = opts.updateSrc

    if opts.method:
        if opts.method[0] == '@':
            opts.method = expandFTPMethod(opts.method)

        anaconda.setMethodstr(opts.method)
    else:
        anaconda.methodstr = None

    if opts.stage2:
        if opts.stage2[0] == '@':
            opts.stage2 = expandFTPMethod(opts.stage2)

        anaconda.stage2 = opts.stage2

    if opts.noverifyssl:
        flags.noverifyssl = True

    if opts.liveinst:
        flags.livecdInstall = True

    if opts.module:
        for mod in opts.module:
            (path, name) = string.split(mod, ":")
            extraModules.append((path, name))

    if opts.vnc:
        flags.usevnc = 1
        opts.display_mode = 'g'
        vncS.recoverVNCPassword()

        # Only consider vncconnect when vnc is a param
        if opts.vncconnect:
            cargs = string.split(opts.vncconnect, ":")
            vncS.vncconnecthost = cargs[0]
            if len(cargs) > 1 and len(cargs[1]) > 0:
                if len(cargs[1]) > 0:
                    vncS.vncconnectport = cargs[1]

    if opts.ibft:
        flags.ibft = 1

    if opts.iscsi:
        flags.iscsi = 1

    if opts.noeject:
        flags.noeject = True

    if opts.targetArch:
        flags.targetarch = opts.targetArch

    # set flags 
    flags.dmraid = opts.dmraid
    flags.mpath = opts.mpath
    flags.selinux = opts.selinux

    if opts.serial:
        flags.serial = True
    if opts.virtpconsole:
        flags.virtpconsole = opts.virtpconsole

    if opts.xdriver:
        anaconda.xdriver = opts.xdriver
        anaconda.writeXdriver()

    # probing for hardware on an s390 seems silly...
    if iutil.isS390():
        opts.isHeadless = True

    if not flags.livecdInstall:
        startAuditDaemon()

    # setup links required for all install types
    for i in ( "services", "protocols", "nsswitch.conf", "joe", "selinux",
               "mke2fs.conf" ):
        try:
            if os.path.exists("/mnt/runtime/etc/" + i):
                os.symlink ("../mnt/runtime/etc/" + i, "/etc/" + i)
        except:
            pass

    # This is the one place we do all kickstart file parsing.
    if opts.ksfile:
        anaconda.isKickstart = True

        kickstart.preScriptPass(anaconda, opts.ksfile)
        ksdata = kickstart.parseKickstart(anaconda, opts.ksfile)
        opts.rescue = opts.rescue or ksdata.rescue.rescue

    if flags.sshd:
        # we need to have a libuser.conf that points to the installer root for
        # sshpw, but after that we start sshd, we need one that points to the
        # install target.
        luserConf = users.createLuserConf(instPath="")
        if anaconda.isKickstart:
            handleSshPw(ksdata)
        startSsh()
        del(os.environ["LIBUSER_CONF"])

    users.createLuserConf(anaconda.rootPath)

    if opts.rescue:
        anaconda.rescue = True

        import rescue, instdata

        anaconda.id = instdata.InstallData(anaconda, [], opts.display_mode)

        if anaconda.isKickstart:
            instClass.setInstallData(anaconda)
            anaconda.id.setKsdata(ksdata)

            # We need an interface before running kickstart execute methods for
            # storage.
            from snack import *
            screen = SnackScreen()
            anaconda.intf = rescue.RescueInterface(screen)

            ksdata.execute()

            anaconda.intf = None
            screen.finish()

            # command line 'nomount' overrides kickstart /same for vnc/
            anaconda.rescue_mount = not (opts.rescue_nomount or anaconda.id.ksdata.rescue.nomount)

        rescue.runRescue(anaconda, instClass)

        # shouldn't get back here
        sys.exit(1)

    if anaconda.isKickstart:
        if ksdata.vnc.enabled:
            flags.usevnc = 1
            opts.display_mode = 'g'

            if vncS.password == "":
                vncS.password = ksdata.vnc.password

            if vncS.vncconnecthost == "":
                vncS.vncconnecthost = ksdata.vnc.host

            if vncS.vncconnectport == "":
                vncS.vncconnectport = ksdata.vnc.port

        flags.vncquestion = False

    #
    # Determine install method - GUI or TUI
    #
    # if display_mode wasnt set by command line parameters then set default
    #
    if not opts.display_mode:
        opts.display_mode = 'g'
    
    # disable VNC over text question when not enough memory is available
    if iutil.memInstalled() < isys.MIN_GUI_RAM:
        flags.vncquestion = False

    if os.environ.has_key('DISPLAY'):
        flags.preexisting_x11 = True

    if opts.display_mode == 't' and flags.vncquestion: #we prefer vnc over text mode, so ask about that
        title = _("Would you like to use VNC?")
        message = _("Text mode provides a limited set of installation options.  "
                    "It does not allow you to specify your own partitioning "
                    "layout or package selections.  Would you like to use VNC "
                    "mode instead?")

        ret = vnc.askVncWindow(title, message)
        if ret != -1:
            opts.display_mode = 'g'
            flags.usevnc = 1
            if ret is not None:
                vncS.password = ret

    if opts.debug:
        flags.debug = True

    import instdata

    import system_config_keyboard.keyboard as keyboard

    log.info("anaconda called with cmdline = %s" %(sys.argv,))
    log.info("Display mode = %s" %(opts.display_mode,))
    log.info("Default encoding = %s " % sys.getdefaultencoding())

    # check memory again, with the real display mode:
    check_memory(opts)

    # this lets install classes force text mode instlls
    if instClass.forceTextMode:
        stdoutLog.info(_("Install class forcing text mode installation"))
        opts.display_mode = 't'

    #
    # find out what video hardware is available to run installer
    #

    # XXX kind of hacky - need to remember if we're running on an existing
    #                     X display later to avoid some initilization steps
    if os.environ.has_key('DISPLAY') and opts.display_mode == 'g':
        x_already_set = 1
    else:
        x_already_set = 0

    #
    # now determine if we're going to run in GUI or TUI mode
    #
    # if no X server, we have to use text mode
    if not x_already_set and (not iutil.isS390() and not os.access("/usr/bin/Xorg", os.X_OK)):
         stdoutLog.warning(_("Graphical installation is not available. "
                             "Starting text mode."))
         time.sleep(2)
         opts.display_mode = 't'

    if opts.isHeadless: # s390/iSeries checks
        if opts.display_mode == 'g' and not (flags.preexisting_x11 or flags.usevnc):
            stdoutLog.warning(_("DISPLAY variable not set. Starting text mode."))
            opts.display_mode = 't'
            graphical_failed = 1
            time.sleep(2)

    # if DISPLAY not set either vnc server failed to start or we're not
    # running on a redirected X display, so start local X server
    if opts.display_mode == 'g' and not flags.preexisting_x11 and not flags.usevnc:
        try:
            # The following code depends on no SIGCHLD being delivered, possibly
            # only except the one from a failing X.org. Thus make sure before
            # entering this section that all the other children of anaconda have
            # terminated or were forked into an orphan (which won't deliver a
            # SIGCHLD to mess up the fragile signaling below).

            # start X with its USR1 handler set to ignore.  this will make it send
            # us SIGUSR1 if it succeeds.  if it fails, catch SIGCHLD and bomb out.

            def sigchld_handler(num, frame):
                raise OSError(0, "SIGCHLD caught when trying to start the X server.")

            def sigusr1_handler(num, frame):
                log.debug("X server has signalled a successful start.")

            def preexec_fn():
                signal.signal(signal.SIGUSR1, signal.SIG_IGN)

            old_sigusr1 = signal.signal(signal.SIGUSR1, sigusr1_handler)
            old_sigchld = signal.signal(signal.SIGCHLD, sigchld_handler)
            xout = open("/dev/tty5", "w")

            proc = subprocess.Popen(["Xorg", "-br", "-logfile", "/tmp/X.log",
                                     ":1", "vt6", "-s", "1440", "-ac",
                                     "-nolisten", "tcp", "-dpi", "96",
                                     "-noreset"],
                                     close_fds=True, stdout=xout, stderr=xout,
                                     preexec_fn=preexec_fn)

            signal.pause()

            os.environ["DISPLAY"] = ":1"
            doStartupX11Actions()
            xserver_pid = proc.pid

            # STACKI
            # 
            # start a VNC server and attach it to the X display
            # 
            # only allow connections from localhost
            # 
            file = open('/tmp/vnchosts', 'w')
            file.write('+127.0.0.1\n')
            file.write('-\n')
            file.close()

            stackproc = subprocess.Popen(['/usr/bin/x0vncserver',
                '-display=:1', '-SecurityTypes=None', '-NeverShared=on',
                '-HostsFile=/tmp/vnchosts'], close_fds=True, stdout=xout,
                stderr=xout)
            # STACKI

        except (OSError, RuntimeError):
            stdoutLog.warning(" X startup failed, falling back to text mode")
            opts.display_mode = 't'
            graphical_failed = 1
            time.sleep(2)
        finally:
            signal.signal(signal.SIGUSR1, old_sigusr1)
            signal.signal(signal.SIGCHLD, old_sigchld)

    set_x_resolution(opts.runres)

    if opts.display_mode == 't' and graphical_failed and not anaconda.isKickstart:
        ret = vnc.askVncWindow()
        if ret != -1:
            opts.display_mode = 'g'
            flags.usevnc = 1
            if ret is not None:
                vncS.password = ret

    # if they want us to use VNC do that now
    if opts.display_mode == 'g' and flags.usevnc:
        runVNC()
        doStartupX11Actions()

    anaconda.setInstallInterface(opts.display_mode)

    anaconda.setBackend(instClass)

    anaconda.id = instClass.installDataClass(anaconda, extraModules, opts.display_mode, anaconda.backend)

    anaconda.id.x_already_set = x_already_set

    anaconda.id.setDisplayMode(opts.display_mode)
    instClass.setInstallData(anaconda)

    # comment out the next line to make exceptions non-fatal
    from exception import initExceptionHandling
    anaconda.mehConfig = initExceptionHandling(anaconda)

    # add our own additional signal handlers
    signal.signal(signal.SIGUSR2, lambda signum, frame: anaconda.dumpState())

    anaconda.setDispatch()

    # download and run Dogtail script
    if opts.dogtail:
       try:
           import urlgrabber

           try:
               fr = urlgrabber.urlopen(opts.dogtail)
           except urlgrabber.grabber.URLGrabError, e:
               log.error("Could not retrieve Dogtail script from %s.\nError was\n%s" % (opts.dogtail, e))
               fr = None
                           
           if fr:
               (fw, testcase) = mkstemp(prefix='testcase.py.', dir='/tmp')
               os.write(fw, fr.read())
               fr.close()
               os.close(fw)
               
               # download completed, run the test
               if not os.fork():
                   # we are in the child
                   os.chmod(testcase, 0o755)
                   os.execv(testcase, [testcase])
                   sys.exit(0)
               else:
                   # we are in the parent, sleep to give time for the testcase to initialize
                   # todo: is this needed, how to avoid possible race conditions
                   time.sleep(1)
       except Exception, e:
           log.error("Exception %s while running Dogtail testcase" % e)

    if opts.lang:
        # this is lame, but make things match what we expect (#443408)
        opts.lang = opts.lang.replace(".utf8", ".UTF-8")
        anaconda.dispatch.skipStep("language", permanent = 1)
        anaconda.id.instLanguage.instLang = opts.lang
        anaconda.id.instLanguage.systemLang = opts.lang
        anaconda.id.timezone.setTimezoneInfo(anaconda.id.instLanguage.getDefaultTimeZone(anaconda.rootPath))

    if opts.keymap:
        anaconda.dispatch.skipStep("keyboard", permanent = 1)
        anaconda.id.keyboard.set(opts.keymap)
        anaconda.id.keyboard.activate()

    if anaconda.isKickstart:
        import storage

        anaconda.id.setKsdata(ksdata)

        # Before we set up the storage system, we need to know which disks to
        # ignore, etc.  Luckily that's all in the kickstart data.
        anaconda.id.storage.zeroMbr = ksdata.zerombr.zerombr
        anaconda.id.storage.ignoreDiskInteractive = ksdata.ignoredisk.interactive
        anaconda.id.storage.ignoredDisks = ksdata.ignoredisk.ignoredisk
        anaconda.id.storage.exclusiveDisks = ksdata.ignoredisk.onlyuse

        if ksdata.clearpart.type is not None:
            anaconda.id.storage.clearPartType = ksdata.clearpart.type
            anaconda.id.storage.clearPartDisks = ksdata.clearpart.drives
            if ksdata.clearpart.initAll:
                anaconda.id.storage.reinitializeDisks = ksdata.clearpart.initAll

        storage.storageInitialize(anaconda, examine_all=False)

        # STACKI
        if os.path.exists('/tmp/stack-skip-welcome'):
            discovered_disks = []
            for d in anaconda.id.storage.disks:
                if not d.removable:
                    discovered_disks.append(d.name)
    
            swraid = []
            for d in anaconda.id.storage.devices:
                if d.name[0:2] == 'md':
                    swraid.append(d.name)
    
            log.info("STACKI:writing discovered.disks")
            diskfile = open('/tmp/discovered.disks', 'w')
            diskfile.write('disks: %s\n' % (' '.join(discovered_disks)))
            diskfile.write('raids: %s\n' % (' '.join(swraid)))
            diskfile.close()
    
            kickstart.preScriptPass(anaconda, opts.ksfile)
            os.system('/opt/stack/lib/do_partition.py > /tmp/partition-info')
            ksdata = kickstart.parseKickstart(anaconda, opts.ksfile)
    
            anaconda.id.setKsdata(ksdata)
    
            # Before we set up the storage system, we need to know which disks
            # to ignore, etc.  Luckily that's all in the kickstart data.
            anaconda.id.storage.zeroMbr = ksdata.zerombr.zerombr
            anaconda.id.storage.ignoreDiskInteractive = \
                ksdata.ignoredisk.interactive
            anaconda.id.storage.ignoredDisks = ksdata.ignoredisk.ignoredisk
            anaconda.id.storage.exclusiveDisks = ksdata.ignoredisk.onlyuse
    
            if ksdata.clearpart.type is not None:
                anaconda.id.storage.clearPartType = ksdata.clearpart.type
                anaconda.id.storage.clearPartDisks = ksdata.clearpart.drives
                if ksdata.clearpart.initAll:
                    anaconda.id.storage.reinitializeDisks = \
                        ksdata.clearpart.initAll
    
            storage.storageInitialize(anaconda)
        # STACKI

        # Now having initialized storage, we can apply all the other kickstart
        # commands.  This gives us the ability to check that storage commands
        # are correctly formed and refer to actual devices.
        ksdata.execute()

    # set up the headless case
    if opts.isHeadless == 1:
        anaconda.id.setHeadless(opts.isHeadless)
        anaconda.dispatch.skipStep("keyboard", permanent = 1)

    if not anaconda.isKickstart:
        instClass.setSteps(anaconda)
    else:
        kickstart.setSteps(anaconda)

    try:
        anaconda.intf.run(anaconda)
    except SystemExit, code:
        anaconda.intf.shutdown()

    if anaconda.isKickstart and anaconda.id.ksdata.reboot.eject:
        for drive in anaconda.id.storage.devicetree.devices:
            if drive.type != "cdrom":
                continue

            log.info("attempting to eject %s" % drive.path)
            drive.eject()

    del anaconda.intf

    # STACKI
    # 
    # There is a strange interaction with ekv and RHEL 6.x. After anaconda
    # completes, it is restarted. The code below ensures that anaconda only
    # runs once.
    # 
    killem = 1
    proc_cmdline = open('/proc/cmdline', 'r')
    for pline in proc_cmdline.readlines():
        if 'build' in pline:
            killem = 0
    proc_cmdline.close()

    if killem:
        os.system('/usr/bin/killall csp')
        os.system('/usr/bin/killall draino')
        os.system('/usr/bin/killall detour')
        os.system('/usr/bin/killall /usr/bin/python')
    # STACKI

# vim:tw=78:ts=4:et:sw=4
