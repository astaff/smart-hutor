'''
Created on Dec 8, 2011

@author: artyomastafurov
'''
import httplib

baseurl   = "smart-hutor.appspot.com"

for i in range(10000):
    connection = httplib.HTTPConnection(baseurl)
    connection.request("GET", "/queue/device1/all")
    res = connection.getresponse()
    
    if (i % 100 == 0):
        print "%s : %s" % (i, res.status)
