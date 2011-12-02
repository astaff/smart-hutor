#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import logging

from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext import db
from django.utils import simplejson


class Node(db.Model):
    address = db.IntegerProperty()
    name = db.StringProperty()
    
class Command(db.Model):
    node = db.ReferenceProperty(reference_class = Node, collection_name = 'commands')
    pin = db.IntegerProperty()
    name = db.StringProperty()
    
class QueueDev1(db.Model):
    command = db.ReferenceProperty(reference_class = Command, collection_name= 'queue_instances', name = "device1")
    id = db.IntegerProperty()

class QueueThermWest(db.Model):
    command = db.ReferenceProperty(reference_class = Command, collection_name= 'queue_instances2', name = "therm_west")
    id = db.IntegerProperty()

class MainHandler(webapp.RequestHandler):
    def get(self):
        self.response.out.write('Hello world!!!')

class DeviceCommandHandler(webapp.RequestHandler):
    def get(self):

        s = self.request.path
        tokens = s.split('/')

        if len(tokens) < 4: 
            logging.error("Unsupported device request " + s)
            self.error(403)
            return 
            
        node = Node.all().filter('name =', tokens[2]).get()
        if node == None :
            logging.error("Unsupported device " + tokens[2] + " in request " + s)           
            self.error(403)
            return
        
        c = node.commands.filter('name =', tokens[3]).get()
        if c == None :
            logging.error("Unsupported command " + tokens[3] + " in request " + s)           
            self.error(403)
            return
        
        # put command into the right queue for device
        if node.name == 'device1':
            q = QueueDev1()
        else:
            q = QueueThermWest()

        logging.info("Adding command '%s' to queue for device '%s'" % (tokens[3], tokens[2]));

        q.command = c
        q.put()


class QueueCommandHandler(webapp.RequestHandler):
    def get(self):
        results = []

        s = self.request.path
        tokens = s.split('/')

        if len(tokens) < 4: 
            self.error(403)
            return 

        # identify the queue
        if tokens[2] == "device1":
            #logging.info("Queue command handler: dev1")
            items = QueueDev1.all()
            q = QueueDev1
        elif tokens[2] == "therm_west":
            #logging.info("Queue command handler: therm_west")
            items = QueueThermWest.all()
            q = QueueThermWest
        else:
            logging.error("Unsupported queue " + tokens[2] + "in request " + s)
            self.error(403)
            return

        # process clear
        if tokens[3] == "all":
            #logging.info("Queue command handler: all")
            for queue_item in items:
                results.append((queue_item.command.node.address, queue_item.command.pin))

        elif tokens[3] == "clear":
            #logging.info("Queue command handler: clear")
            db.delete(items)
            
        else:
            logging.error("Unsupported action " + tokens[3] + "in request " + s)
            self.error(403)
            return
          
        self.response.out.write(simplejson.dumps(results))

        
class CleanupHandler(webapp.RequestHandler):
    def get(self):
        db.delete(QueueDev1.all())
        db.delete(QueueThermWest.all())
        db.delete(Command.all())
        db.delete(Node.all())  

class SetupHandler(webapp.RequestHandler):
    def get(self):
        newNode = Node(address = int("0x0013a200403bc53a", 0), name = 'device1')
        newNode.put()
        Command(node = newNode, pin = 0, name = "on").put()  
        Command(node = newNode, pin = 1, name = "off").put()

        newNode2 = Node(address = int("0x0013a200403bc53b", 0), name = 'therm_west')
        newNode2.put()
        Command(node = newNode2, pin = 0, name = "on").put()  
        Command(node = newNode2, pin = 1, name = "off").put()

def main():   
    # supported URLs:
    # /device/[device1|therm_west]/[on|off]
    # /queue/[device1|therm_west]/[all|clear]

    application = webapp.WSGIApplication([
                                          ('/dev/.*', DeviceCommandHandler),
                                          ('/queue/.*',  QueueCommandHandler),
                                          ('/cleanup', CleanupHandler),
                                          ('/setup', SetupHandler)
                                          ],
                                     debug=True)
 
#    application = webapp.WSGIApplication([('/', MainHandler)],
#                                         debug=True)
    
    # on startup, re-run cleanup & setup nodes
    CleanupHandler()
    SetupHandler()

    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
