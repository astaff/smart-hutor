#!/bin/env python

# modifications to baseline:
# - only clear the queue if something was retrieved from it
# - support for GPIO mode of operation - default is via WL520GU WLAN LED
# - parameters for specifying server device, GPIO line, base URL

import time
import os 
from optparse import OptionParser
import httplib
import datetime
import socket

# the normal way would be to use pack, but it doesn't work properly on 
# asus' processor
def int_to_str(source):
    s = ""    
    for i in range(8):
        s = chr(source & 0xFF) + s
        source >>= 8
    return s

pin_mappings = {0:'D0',1:'D1',2:'D2'}

# default options
baseurl   = "smart-hutor.appspot.com"
gpio      = "/proc/diag/led/wlan"
gpio_mode = False
sdevice   = "device1"
interval  = 1

parser = OptionParser()
parser.add_option("-m", "--modem", dest="filename", 
                  help="Device path XBee is attached to", 
                  metavar="FILE")
parser.add_option("-u", "--base-url", dest="baseurl", 
                  help="Base URL for the application, without http:// prefix; default: " + baseurl, 
                  metavar="URL")
parser.add_option("-l", "--gpio-line", dest="gpio", 
                  help="File representing GPIO line, default: " + gpio, 
                  metavar="GPIO")
parser.add_option("-g", "--gpio-mode", dest="gpio_mode", action="store_true",
                  help="Run in GPIO mode, default is Zigbee mode")
parser.add_option("-d", "--server-device", dest="sdevice", 
                  help="Device queue on the server, default:  " + sdevice)
parser.add_option("-i", "--interval", dest="interval", type="int",
                  help="Polling interval:  %s" % interval)


(options, args) = parser.parse_args()

if options.baseurl != None:
    baseurl = options.baseurl

if options.gpio != None:
    gpio = options.gpio

if options.gpio_mode == True:
    gpio_mode = True

if options.sdevice != None:
    sdevice = options.sdevice

if options.interval != None:
    interval = options.interval

# print options summary
print "Running with options:"
if gpio_mode:
    print "  gpio mode"
    print "  gpio line = %s" % gpio
else:
    print "  zigbee mode"
    print "  modem     = %s" % options.filename

print     "  baseurl   = %s" % baseurl
print     "  device    = %s" % sdevice
print     "  interval  = %d" % interval

# conditionally configure for zigbee 
# hack:  zigbee router has simplejson, xbee and serial modules installed, GPIO router has regular json
if not gpio_mode:
    from xbee import ZigBee
    import simplejson as json
    import serial

    if options.filename is None :
        print "--modem=PATH is required. Please provide a full device path to the serial port XBee is attached to"
        os._exit(0)

        ser = serial.Serial(options.filename, 9600)
        time.sleep(0.2)

        xbee = ZigBee(ser)
else:
    import json

# main loop
while True :
    try:
        connection = httplib.HTTPConnection(baseurl)
        connection.request("GET", "/queue/" + sdevice + "/all")
        res = connection.getresponse()

        if (res.status == 200):
            s = res.read()
            queue = json.loads(s)

            # only clear queue if messages were retrieved from it
            if len(queue):
                connection.request("GET", "/queue/" + sdevice + "/clear")
                connection.getresponse()

            now = datetime.datetime.now()

            for item in queue:      

                # log the action taken
                if item[1] == 0:
                    print "%s: switching to high" % now
                    resp = "/ack_on"
                else:
                    print "%s: switching to low" % now
                    resp = "/ack_off"

                if not gpio_mode:
                    # addr2 = '\x00\x13\xa2\x00\x40\x3b\xc5\x3a'
                    addr = int_to_str(item[0])
                    xbee.remote_at(dest_addr_long=addr, command=pin_mappings[2], parameter='\x05')
                    time.sleep(0.2) 
                    xbee.remote_at(dest_addr_long=addr, command=pin_mappings[item[1]], parameter='\x05')
                    time.sleep(0.5)        
                    xbee.remote_at(dest_addr_long=addr, command=pin_mappings[item[1]], parameter='\x04')
                    time.sleep(0.2)                
                    xbee.remote_at(dest_addr_long=addr, command=pin_mappings[2], parameter='\x04')
                    time.sleep(0.2) 
                else:
                    if item[1] == 0:
                        ret = os.system("echo 1 > " + gpio)
                    else:
                        ret = os.system("echo 0 > " + gpio)

                    if ret:
                        print "Error setting the GPIO line"
                
                # ack the state transition back to the server
                connection.request("GET", "/state/" + sdevice + resp)
                connection.getresponse()

        time.sleep(interval)

    except socket.error as (e, s):
        print "Exception occurred: '%s [%d]'.  Waiting 10 seconds and retrying." % (s, e)
        time.sleep(10)

if not gpio_mode:    
    ser.close()
