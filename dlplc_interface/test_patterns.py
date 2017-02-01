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


def main():
    dlplc = LightCrafterTCP()
    if not dlplc.connect():
        return 1
    v = dlplc.cmd_version_string(0x00)
    print "DM365 SW Revision: %s"%v.data
    v = dlplc.cmd_version_string(0x10)
    print "FPGA Firmware Revision: %s"%v.data
    v = dlplc.cmd_version_string(0x20)
    print "MSP430 SW Revision: %s"%v.data
    print ""

    v = dlplc.cmd_current_display_mode(0x01)
    print "Current display mode: %s"%":".join(c.encode('hex') for c in v.data)
    for i in range(13):
        raw_input("Press Enter to display testpatern %d/13..."%(i+1))
        dlplc.cmd_current_test_pattern(i)

    dlplc.close()
    

if __name__ == "__main__":
    main()
