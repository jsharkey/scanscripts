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

import SimpleHTTPServer
import SocketServer
import urlparse
import threading

'''

This script is a web server that prompts people for the correct orientation
of all found photos.  Users hit the arrow key that represents "which way is
up" which then kicks off a rotation job and hands out the next photo.  This
script scales to any number of users.

It sets the +x bit to indicate which files have been correctly rotated, and
it touches a file to indicate what rotation the user chose.

'''

# figure out all images to be done
path = sys.argv[1]
todo = []
for dirpath, dnames, fnames in os.walk(path):
    for f in fnames:
        if f.endswith(".png") and os.stat(f).st_mode == 0100644:
            todo.append(f)

todo = sorted(todo)
print "found", len(todo), "files remaining"


class Async(threading.Thread):
    def __init__(self, f, r):
        threading.Thread.__init__(self)
        self.f = f
        self.r = r

    def run(self):
        if os.stat(self.f).st_mode == 0100644:
            subprocess.check_call(["mogrify", "-rotate", self.r, self.f])
            subprocess.check_call(["touch", "%s.rot%s" % (self.f, self.r)])
            os.chmod(self.f, 0100655)
            print "DONE!"
        else:
            print "OMG!"



class MyRequestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    def do_GET(self):
        global todo
        parsed = urlparse.urlparse(self.path)
        query = urlparse.parse_qs(parsed.query)
        if parsed.path == '/':
            f = todo.pop()
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write("""

<body>
<p>working with %s
<p>
<img src="%s" id="im" style="height:75  %%" />
</body>
<script>

document.onkeydown = function(evt) {
    // left=37, right=39, up=38, dow=40
    evt = evt || window.event;
    if(evt.keyCode==40) { r=180; }
    else if(evt.keyCode==39) { r=270; }
    else if(evt.keyCode==38) { r=0; }
    else if(evt.keyCode==37) { r=90; }
    else { return; }

    document.getElementById("im").src="";
    document.location.href="/rotate?f=%s&r="+r;
};

</script>

""" % (f,f,f))
        elif parsed.path == '/rotate':
            # {'r': ['90'], 'f': ['./path/to/foo.png']}
            f = query['f'][0]
            r = query['r'][0]

            Async(f, r).start()

            self.send_response(302)
            self.send_header("Location", "/")
            self.end_headers()
        else:
            return SimpleHTTPServer.SimpleHTTPRequestHandler.do_GET(self)

PORT = 8000
SocketServer.TCPServer.allow_reuse_address = True
httpd = SocketServer.TCPServer(("", PORT), MyRequestHandler)

print "serving at port", PORT
try:
    httpd.serve_forever()
except KeyboardInterrupt:
    httpd.shutdown()
