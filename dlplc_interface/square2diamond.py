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

#from dlplc_tcp import *
import argparse
import sys

from PIL import Image

def square2diamond(source):
    width = 608
    height = 684
    dest = Image.new("1", (width,height), 0)
   
    if source.mode != "1":
        print "Warning: Mode of source file is not 1 bit."
        print "Will convert."
        source = source.convert("1")

    source_pix = source.load()
    dest_pix = dest.load()

    for x in range(0, height):
        for y in range(0, width):
            if x%2 == 0:
                q = width + x/2 - y
                r = x/2 + y
            else:
                q = width + (x-1)/2 - y
                r = 1 + (x-1)/2 + y
            try:
                dest_pix[y,x] = source_pix[q,r]
            except Exception as e:
                print e
                print "({}, {}) <- ({}, {})".format(x,y,q,r)
                print "Is the source file big enough?"
    return dest

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", help="The image file to convert.")
    args = parser.parse_args()

    source = Image.open(args.source)
    dest = square2diamond(source)
    dest.save(args.source[:-4]+".diamond.bmp")

