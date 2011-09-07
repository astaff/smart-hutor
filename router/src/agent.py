from xbee import ZigBee
import time
import serial
import os 
from optparse import OptionParser
import httplib
import simplejson as json

# the normal way would be to use pack, but it doesn't work properly on 
# asus' processor
def int_to_str(source):
    s = ""    
    for i in range(8):
        s = chr(source & 0xFF) + s
        source >>= 8
    return s

pin_mappings = {0:'D0',1:'D1'}

parser = OptionParser()
parser.add_option("-m", "--modem", dest="filename", 
                  help="Device path XBee is attached to", 
                  metavar="FILE")

(options, args) = parser.parse_args()

if options.filename is None :
    print "--modem=PATH is required. Please provide a full device path to the serial port XBee is attached to"
    os._exit(0)

ser = serial.Serial(options.filename, 9600)
time.sleep(0.2)

xbee = ZigBee(ser)

while True :
    connection = httplib.HTTPConnection("smart-hutor.appspot.com")
    connection.request("GET", "/queue/all")
    res = connection.getresponse()

    if (res.status == 200):
        s = res.read()
        queue = json.loads(s)
        connection.request("GET", "/queue/clear")
        connection.getresponse()
        
        for item in queue:        
            # addr2 = '\x00\x13\xa2\x00\x40\x3b\xc5\x3a'
            addr = int_to_str(item[0])
            xbee.remote_at(dest_addr_long=addr, command=pin_mappings[item[1]], parameter='\x05')
            time.sleep(0.5)        
            xbee.remote_at(dest_addr_long=addr, command=pin_mappings[item[1]], parameter='\x04')
            time.sleep(0.2)
    time.sleep(1)
    
ser.close()