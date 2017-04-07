#!/usr/bin/python2
print "Content-type: text/html\n"
print

import cgitb; cgitb.enable()
print "<title>Testtitle</title>"
print """
hello there
"""
print 1/0
