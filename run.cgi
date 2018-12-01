#!/home/thewhit1/public_html/cgi-bin/flask/bin/python
import sys
sys.path.insert(0, '/home/thewhit1/public_html/mas')

# Enable CGI error reporting
import cgitb
cgitb.enable()

import os
from wsgiref.handlers import CGIHandler

app = None
try:
	import application
	app = application.app
except Exception, e:
	print "Content-type: text/html"
	print
	cgitb.handler()
	exit()

os.environ['SERVER_NAME'] = 'thewhitebeards.com'
os.environ['SERVER_PORT'] = '80'
os.environ['REQUEST_METHOD'] = 'GET'

class ScriptNameStripper(object):
   def __init__(self, app):
       self.app = app

   def __call__(self, environ, start_response):
       environ['SCRIPT_NAME'] = ''
       return self.app(environ, start_response)

app = ScriptNameStripper(app)

try:
	CGIHandler().run(app)
except Exception, e:
	print "Content-type: text/html"
	print
	cgitb.handler()
	exit()