#!/usr/bin/python

'''
    Copyright 2016, Jeff Sharkey

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

from PIL import Image

import numpy
import os
import sys
import math
import subprocess

'''

This script looks at scanned TIF images and tries figuring out what layout
various photos are in:

2 photos: two large photos in adjacent corners
4 photos: one in each corner of scan
5 photos: three vertical, two horizontal

It does this by looking for the white space between photos for each
layout.  Once the layout is determined, we assume rough rectangles and
then "probe" inwards from each direction until we find non-white areas,
and assume that's a valid crop.

This also handles the cases where the 2 and 5 photo layouts could have
been flipped along an axis by the user at scan time.

Assumes 300 DPI scans with resolution 3508x2544.

'''


BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)

def format(fg=None, bg=None, bright=False, bold=False, dim=False, reset=False):
    # manually derived from http://en.wikipedia.org/wiki/ANSI_escape_code#Codes
    codes = []
    if reset: codes.append("0")
    else:
        if not fg is None: codes.append("3%d" % (fg))
        if not bg is None:
            if not bright: codes.append("4%d" % (bg))
            else: codes.append("10%d" % (bg))
        if bold: codes.append("1")
        elif dim: codes.append("2")
        else: codes.append("22")
    return "\033[%sm" % (";".join(codes))


debug = False

def is_white(det):
    global debug
    mean = numpy.mean(det, axis=(0,1))
    std = numpy.std(det, axis=(0,1))
    if debug:
        print "\t", mean, std
    for n in mean:
        if n < 210 or math.isnan(n): return False
    for n in std:
        if n > 10 or math.isnan(n): return False
    return True

def is_pixel_white(p):
    for n in p:
        if n < 220 or math.isnan(n): return False
    return True


def detect5a(ar):
    global debug
    if debug: print "detect5a:"
    target = 1485
    for i in range(target-50,target+50,10):
        if is_white(ar[:,i:i+2,:]): return True
    return False

def detect5b(ar):
    global debug
    if debug: print "detect5b:"
    target = 1200
    for i in range(target-100,target+100,10):
        if is_white(ar[i:i+2,:1400,:]): return True
    return False

def detect6(ar):
    global debug
    if debug: print "detect6:"
    target = 1200
    for i in range(target-100,target+100,10):
        if is_white(ar[i:i+2,:,:]): return True
    return False

def detect4(ar):
    global debug
    if debug: print "detect4:"
    target = 1272
    for i in range(target-50,target+50,10):
        if is_white(ar[:,i:i+2,:]): return True
    return False

def detect2(ar):
    global debug
    if debug: print "detect2:"
    target = 2100
    for i in range(target-50,target+50,10):
        if is_white(ar[:,i:i+2,:]): return True
    return False


def rev(slots):
    def flip(slot):
        x1,y1,x2,y2 = slot
        return (2543-x2,y1,2543-x1,y2)
    return [ flip(slot) for slot in slots ]

slots6 = [ (0,0,1480,1120), (0,1120,1480,2400), (0,2400,1480,3507), (1480,0,2543,1120), (1480,1120,2543,2400), (1480,2400,2543,3507), ]
slots6r = rev(slots6)
slots5 = [ (0,0,1480,1120), (0,1120,1480,2400), (0,2400,1480,3507), (1480,0,2543,1800), (1480,1800,2543,3507) ]
slots5r = rev(slots5)
slots4 = [ (0,0,1270,1775),                     (0,1775,1270,3507), (1270,0,2543,1775), (1270,1775,2543,3507) ]
slots2 = [ (0,0,2543,1775),                     (0,1775,2543,3507) ]
slots2r = rev(slots2)


def probe_hor(ar, xx, y):
    for x in xx:
        if not is_pixel_white(ar[y,x]): return x
    return -1

def probe_vert(ar, x, yy):
    for y in yy:
        if not is_pixel_white(ar[y,x]): return y
    return -1

def best_crop(ar, slot):
    global debug
    left, top, right, bottom = slot
    xhalf = (left+right)/2
    yhalf = (top+bottom)/2

    left = probe_hor(ar, range(left,left+1000), yhalf)
    right = probe_hor(ar, range(right,right-1000,-1), yhalf)
    top = probe_vert(ar, xhalf, range(top,top+1000))
    bottom = probe_vert(ar, xhalf, range(bottom,bottom-1000,-1))

    if left == -1 or top == -1 or right == -1 or bottom == -1:
        slot2 = None
    else:
        slot2 = (left, top, right, bottom)
    if debug: print "\t", str(slot).ljust(30), "-->", slot2
    return slot2


def detect_orient(f):
    global debug
    im = Image.open(f)
    ar = numpy.array(im)
    ar2 = ar[:,::-1,:]
    slots = []

    print "\n", f,
    if detect5a(ar) and detect6(ar): print "%s 6UP %s" % (format(RED), format(reset=True)),; slots = slots6
    elif detect5a(ar2) and detect6(ar): print "%s 6RUP %s" % (format(RED), format(reset=True)),; slots = slots6r
    elif detect5a(ar) and detect5b(ar): print "%s 5UP %s" % (format(BLUE), format(reset=True)),; slots = slots5
    elif detect5a(ar2) and detect5b(ar2): print "%s 5RUP %s" % (format(YELLOW), format(reset=True)),; slots = slots5r
    elif detect4(ar): print "%s 4UP %s" % (format(GREEN), format(reset=True)),; slots = slots4
    elif detect2(ar): print "%s 2UP %s" % (format(CYAN), format(reset=True)),; slots = slots2
    elif detect2(ar2): print "%s 2RUP %s" % (format(MAGENTA), format(reset=True)),; slots = slots2r
    else:
        print "%s UNKNOWN %s" % (format(BLACK, RED), format(reset=True))
        debug = True
        detect5a(ar)
        detect5b(ar)
        detect5a(ar2)
        detect5b(ar2)
        detect4(ar)
        detect2(ar)
        debug = False

    sys.stdout.flush()
    #slots = []

    # figure out exact cropping
    for i in range(len(slots)):
        slot = slots[i]
        slot = best_crop(ar, slot)
        if slot is None: continue

        # TODO: actually crop and output lossless webp
        # wxh+x+y
        left, top, right, bottom = slot
        width = right - left
        height = bottom - top
        out = "%s.%02d.png" % (f, i)
        subprocess.call(["convert", "-crop", "%dx%d+%d+%d" % (width, height, left, top), f, out])
        print ".",
        sys.stdout.flush()


path = sys.argv[1]
if os.path.isfile(path):
    detect_orient(path)

for dirpath, dnames, fnames in os.walk(path):
    for f in sorted(fnames):
        #if "20" not in f: continue
        if f.endswith(".tif"):
            detect_orient(os.path.join(dirpath, f))




"""

exiftool  -GPSLatitude=46.0 -GPSLatitudeRef=N -GPSLongitude=92.0 -GPSLongitudeRef=W -GPSAltitude=0 -GPSAltitudeRef='above'  -AllDates='2003:02:01 12:00:00' -Make='EPSON'  test.png -o geo.png
exiftool -AllDates='2003:02:01 00:00:00' -Make='EPSON' -Orientation#=1


1 = Horizontal (normal)
3 = Rotate 180
6 = Rotate 90 CW
8 = Rotate 270 CW


Camera Model Name               : Canon EOS 5D Mark III

FileSource  2 = Reflection Print Scanner

0x010f  Make
0x0110  Model
0x0112  Orientation
0xbc02  Transformation

"""
