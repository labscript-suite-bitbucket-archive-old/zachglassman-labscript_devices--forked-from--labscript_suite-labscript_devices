#!/usr/bin/python2.7
# -*- coding: utf8 -*-
"""
    This file is part of DLPLC Interface.

    DLPLC Interface is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    DLPLC Interface is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with DLPLC Interface.  If not, see <http://www.gnu.org/licenses/>.
"""

from dlplc_tcp import *
import argparse
import sys

def connect():
    """Connect to a dlplc or exit"""
    dlplc = LightCrafterTCP()
    if not dlplc.connect():
        print "Unable to connect to device."
        sys.exit(1)
    return dlplc


def display_sequence(path, settings={}):
    dlplc = connect()
    images = []
    num = 0
    for i in range(96):
        try:
            with open("%s%02d.bmp"%(path, i), mode="rb") as f:
                data = f.read()
            images.append(data)
            num+=1
        except:
            break
    settings["num"] = num

    try:
        dlplc.cmd_current_display_mode(0x04)
        dlplc.cmd_start_pattern_sequence(False)
        dlplc.cmd_pattern_sequence_setting(settings)
        print "Uploading %d images..."%num
        dlplc.cmd_pattern_definition(images)
        print "    Done."

        dlplc.cmd_start_pattern_sequence(True)
    except Error as e:
        print e
        return 1

    dlplc.close()
    return 0

def get_version():
    dlplc = connect()
    v = dlplc.cmd_version_string(0x00)
    print "DM365 SW Revision: %s"%v.data
    v = dlplc.cmd_version_string(0x10)
    print "FPGA Firmware Revision: %s"%v.data
    v = dlplc.cmd_version_string(0x20)
    print "MSP430 SW Revision: %s"%v.data
    dlplc.close()
    return 0

def display_bitmap(filename):
    dlplc = connect()
    v = dlplc.cmd_current_display_mode(0x00)
    print "Current display mode: %s"%":".join(c.encode('hex') for c in v.data)

    with open(filename, mode="rb") as f:
        data = f.read()
    #print ":".join(c.encode('hex') for c in data)
    print "Loading image..."
    response = dlplc.cmd_static_image(data);
    print "    Done."

    try:
        response.raise_if_error()
    except:
        print "Error:"
        response.show()
        return 1

    dlplc.close()
    return 0

def interactive():
    dlplc = connect()
    print "The following commands are supported in interactive mode:"
    print " <Return>: advances the pattern."
    print " N: go to pattern N, with N from 0 to 95."
    print " exit: exit the interactive mode."
    
    cmd = "-"
    while cmd != "exit":
        cmd = raw_input("? ")
        if cmd == "":
            try:
                dlplc.cmd_advance_pattern_sequence()
                print "  cmd: advance pattern sequence. Done."
            except Error as e:
                print e
        else:
            print cmd
            try:
                num = int(cmd)
                try:
                    dlplc.cmd_display_pattern(num)
                    print "  cmd: display pattern %d. Done."%num
                except Error as e:
                    print e
            except ValueError:
                print "  Not a valid command."

    dlplc.close()
    return 0


def main(argv):
    action_p = argparse.ArgumentParser(
        epilog="To get help on one specific action, type <action> --help.")
    action_p.add_argument("action", help="The action that shoud be done.",
        choices=("static", "sequence", "version"))

    # parse action args
    action_args = (argv[1],) if len(argv)>= 2 else ()
    action = action_p.parse_args(action_args).action

    # parse sub command arguments
    sub_args = argv[2:]
    parser = argparse.ArgumentParser(prog=argv[0]+" "+action)

    if action=="static":
        parser.description = "Load and display a static image."
        parser.add_argument("-i", "--input", required=True,
            help="The input file in Windows BMP format.")
        args = parser.parse_args(sub_args)
        ret = display_bitmap(args.input)

    elif action=="sequence":
        parser.description = "Load and display a pattern sequence."
        parser.add_argument("-i", "--input", nargs=1,
            help="Location of the patterns. The patterns must be named\
 INPUT_xx.bmp with xx beeing consecutive numbers from 00 to maximum 95.\
Either this option or the interactive option must be given.")
        parser.add_argument("-I", "--interactive", action="store_true",
            help="Start interactive mode to switch patterns.\
Either this option or the input option must be given.")
        parser.add_argument("-n", "--negate", action="store_true",
            help="Each pattern is displayed and followed by its\
inverted pattern before the next pattern is displayed")
        parser.add_argument("-p", "--period", type=int,
            help="Trigger period in micro seconds. Default: 200000",
            default=200000)
        parser.add_argument("-e", "--exposure", type=int,
            help="Exposure time in micro seconds. Default: PERIOD",
            default=0)
        parser.add_argument("-d", "--delay", type=int,
            help="Trigger delay in micro seconds. Default: 0",
            default=0)
        parser.add_argument("-t", "--trigger", nargs=1,
            help="Input trigger type to auto or command trigger. Default: auto",
            default=('auto',), choices=('cmd','auto'))
        parser.add_argument("-c", "--color", nargs=1,
            help="LED selection red, green or blue. Default: red",
            default=('red',), choices=('red','green','blue'))
        args = parser.parse_args(sub_args)
        #print vars(args)
        if args.exposure == 0:
            args.exposure = args.period
        args.led = ('red','green','blue').index(args.color[0])
        args.trigger = ('cmd','auto').index(args.trigger[0])
        args.include_inverted = 1 if args.negate else 0
        if args.input != None:
            ret = display_sequence(args.input[0], vars(args))
        if args.interactive:
            ret = interactive()
        if args.input==None and not args.interactive:
            parser.print_help()
            ret = 1

    elif action=="version":
        ret = get_version()

    return ret

if __name__ == "__main__":
    ret = main(sys.argv)
    sys.exit(ret)
