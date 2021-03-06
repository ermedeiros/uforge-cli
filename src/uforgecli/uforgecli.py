'''
	UForgeCLI
'''

try:
        from urllib.parse import urlencode
except ImportError:
        from urllib import urlencode

import argparse
import getpass
import base64
import httplib2
import os
import sys
import ussclicore.utils.generics_utils
from ussclicore.utils import printer

from ussclicore.cmd import Cmd, CmdUtils
from ussclicore.argumentParser import CoreArgumentParser, ArgumentParser, ArgumentParserError
import commands
from uforge.application import Api
from utils import *


__author__ = "UShareSoft"
__license__ = "Apache License 2.0"





class CmdBuilder(object):
        @staticmethod
        def generateCommands(class_):
                # Create subCmds if not exist
                if not hasattr(class_, 'subCmds'):
                        class_.subCmds = {}

                user = commands.user.User_Cmd()
                class_.subCmds[user.cmd_name] = user

                entitlement = commands.entitlement.Entitlement_Cmd()
                class_.subCmds[entitlement.cmd_name] = entitlement

                subscription = commands.subscription.Subscription_Cmd()
                class_.subCmds[subscription.cmd_name] = subscription

                role = commands.role.Role_Cmd()
                class_.subCmds[role.cmd_name] = role

                images = commands.images.Images_Cmd()
                class_.subCmds[images.cmd_name] = images

                org = commands.org.Org_Cmd()
                class_.subCmds[org.cmd_name] = org

                os = commands.os.Os_Cmd()
                class_.subCmds[os.cmd_name] = os

                pimages = commands.pimages.Pimages_Cmd()
                class_.subCmds[pimages.cmd_name] = pimages

                usergrp = commands.usergrp.Usergrp_Cmd()
                class_.subCmds[usergrp.cmd_name] = usergrp

                template = commands.template.Template_Cmd()
                class_.subCmds[template.cmd_name] = template

## Main cmd
class Uforgecli(Cmd):
        #subCmds = {
        #       'tools': CmdUtils
        #}
        def __init__(self):
                super(Uforgecli, self).__init__()
                self.prompt = 'uforge-cli >'

        def do_exit(self, args):
                return True

        def do_quit(self, args):
                return True

        def arg_batch(self):
                doParser = ArgumentParser("batch", add_help = False, description="Execute uforge-cli batch command from a file (for scripting)")
                mandatory = doParser.add_argument_group("mandatory arguments")
                optionnal = doParser.add_argument_group("optional arguments")
                mandatory.add_argument('--file', dest='file', required=True, help="uforge-cli batch file commands")
                optionnal.add_argument('-f', '--fatal', dest='fatal', action='store_true',required=False, help="exit on first error in batch file (default is to continue)")
                # Help is not call at the doParser declaration because it would create two separate argument group for optional arguments.
                optionnal.add_argument('-h', '--help', action='help', help="show this help message and exit")
                return doParser

        def do_batch(self, args):
                try:
                        doParser = self.arg_batch()
                        try:
                                doArgs = doParser.parse_args(args.split())
                        except SystemExit as e:
                                return
                        with open(doArgs.file) as f:
                                for line in f:
                                        try:
                                                self.run_commands_at_invocation([line])
                                        except:
                                                printer.out("bad command '"+line+"'", printer.ERROR)
                                                # If fatal optionnal argument is specified.
                                                if doArgs.fatal:
                                                        printer.out("Fatal error leading to exit task", printer.ERROR)
                                                        return
                                        print "\n"

                except IOError as e:
                        printer.out("File error: "+str(e), printer.ERROR)
                        return
                except ArgumentParserError as e:
                        printer.out("In Arguments: "+str(e), printer.ERROR)
                        self.help_batch()

        def help_batch(self):
                doParser = self.arg_batch()
                doParser.print_help()

        def cmdloop(self, args):
                if len(args):
                        code = self.run_commands_at_invocation([str.join(' ', args)])
                        sys.exit(code)
                else:
                        self._cmdloop()



def generate_base_doc(app, uforgecli_help):
        myactions=[]
        cmds= sorted(app.subCmds)
        for cmd in cmds:
                myactions.append(argparse._StoreAction(
                        option_strings=[],
                        dest=str(cmd),
                        nargs=None,
                        const=None,
                        default=None,
                        type=str,
                        choices=None,
                        required=False,
                        help=str(app.subCmds[cmd].__doc__),
                        metavar=None))

        return myactions

def set_globals_cmds(subCmds):
        for cmd in subCmds:
                if hasattr(subCmds[cmd], 'set_globals'):
                        subCmds[cmd].set_globals(api, username, password)
                        if hasattr(subCmds[cmd], 'subCmds'):
                                set_globals_cmds(subCmds[cmd].subCmds)


#Generate Uforgecli base command + help base command
CmdBuilder.generateCommands(Uforgecli)
app = Uforgecli()
myactions=generate_base_doc(app, uforgecli_help="")


# Args parsing
mainParser = CoreArgumentParser(add_help=False)
CoreArgumentParser.actions=myactions
mainParser.add_argument('-U', '--url', dest='url', type=str, help='the server URL endpoint to use', required = False)
mainParser.add_argument('-u', '--user', dest='user', type=str, help='the user name used to authenticate to the server', required = False)
mainParser.add_argument('-p', '--password', dest='password', type=str, help='the password used to authenticate to the server', required = False)
mainParser.add_argument('-v', action='version', help='displays the current version of the uforge-cli tool', version="%(prog)s version '"+constants.VERSION+"'")
mainParser.add_argument('-h', '--help', dest='help', action='store_true', help='show this help message and exit', required = False)
mainParser.add_argument('-k', '--publickey', dest='publickey', type=str, help='public API key to use for this request. Default: no default', required = False)
mainParser.add_argument('-s', '--secretkey', dest='secretkey', type=str, help='secret API key to use for this request. Default: no default', required = False)
mainParser.add_argument('-c', '--no-check-certificate', dest='crypt', action="store_true", help='Don\'t check the server certificate against the available certificate authorities', required = False)

mainParser.set_defaults(help=False)
mainParser.add_argument('cmds', nargs='*', help='UForge CLI cmds')
mainArgs, unknown = mainParser.parse_known_args()


if mainArgs.help and not mainArgs.cmds:
        mainParser.print_help()
        exit(0)

if mainArgs.user is not None and mainArgs.url is not None:
        if not mainArgs.password:
                mainArgs.password = getpass.getpass()
        username=mainArgs.user
        password=mainArgs.password
        url=mainArgs.url
        if mainArgs.crypt == True:
                sslAutosigned = True
        else:
                sslAutosigned = False
else:
        mainParser.print_help()
        exit(0)




#UForge API instanciation
client = httplib2.Http(disable_ssl_certificate_validation=sslAutosigned, timeout=constants.HTTP_TIMEOUT)
#activate http caching
#client = httplib2.Http(generics_utils.get_Uforgecli_dir()+os.sep+"cache")
headers = {}
headers['Authorization'] = 'Basic ' + base64.encodestring( username + ':' + password )
api = Api(url, client = client, headers = headers)
set_globals_cmds(app.subCmds)

if mainArgs.help and len(mainArgs.cmds)>=1:
        argList=mainArgs.cmds + unknown;
        argList.insert(len(mainArgs.cmds)-1, "help")
        app.cmdloop(argList)
elif mainArgs.help:
        app.cmdloop(mainArgs.cmds + unknown + ["-h"])
else:
        app.cmdloop(mainArgs.cmds + unknown)
