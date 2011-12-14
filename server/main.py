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
from google.appengine.api import memcache

class Node(db.Model):
    address = db.IntegerProperty()
    name = db.StringProperty()
    on_state = db.BooleanProperty()
    
class Command(db.Model):
    node = db.ReferenceProperty(reference_class = Node, collection_name = 'commands')
    pin = db.IntegerProperty()
    name = db.StringProperty()
    
class Queue(db.Model):
    command = db.ReferenceProperty(reference_class = Command, collection_name= 'queue_instances', name = "device1")
    id = db.IntegerProperty()
    dev_name = db.StringProperty()

class MainHandler(webapp.RequestHandler):
    def get(self):
        self.response.out.write('Hello world!!!')
        
class CacheHandler:
    cache_mappings = {"queue" : Queue, "node" : Node}

    def get_key(self, name, operator, value):
        return "_data_" + name + "_" + operator + "_" + value
        
    def invalidate(self):
        memcache.flush_all()

    def get(self, name, operator, value):
        
        key = self.get_key(name, operator, value)
        results = memcache.get(key = key)
        
        if (results != None):
            None
            # logging.info("Cache hit: %s" % key)
        else:
            # logging.info("Cache miss: %s" % key)
            items = self.cache_mappings[name].all()
            results = [];
            
            if (operator != None):
                items = items.filter(operator, value)
                
            for item in items:
                results.append(item)
                        
            memcache.set(key = key, value = results)
            
        return results                

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
        
        # add command to the queue
        q = Queue()

        logging.info("Adding command '%s' to queue for device '%s'" % (tokens[3], tokens[2]))

        q.command  = c
        q.dev_name = tokens[2]
        q.put()
        cache.invalidate()


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
            None
        elif tokens[2] == "therm_west":
            #logging.info("Queue command handler: therm_west")
            None
        else:
            logging.error("Unsupported queue " + tokens[2] + "in request " + s)
            self.error(403)
            return

        # filter to only items destined for this device
        # items = Queue.all()
        items = cache.get("queue", "dev_name = ", tokens[2])
        # items.filter("dev_name = ", tokens[2])

        # process clear
        if tokens[3] == "all":
            #logging.info("Queue command handler: all")
            for queue_item in items:
                results.append((queue_item.command.node.address, queue_item.command.pin))

        elif tokens[3] == "clear":
            #logging.info("Queue command handler: clear")
            db.delete(items)
            cache.invalidate()
            
        else:
            logging.error("Unsupported action " + tokens[3] + "in request " + s)
            self.error(403)
            return
          
        self.response.out.write(simplejson.dumps(results))

class StateHandler(webapp.RequestHandler):
    def get(self):

        s = self.request.path
        tokens = s.split('/')

        if len(tokens) < 4: 
            logging.error("Unsupported device request " + s)
            self.error(403)
            return 
            
        # node = Node.all().filter('name =', tokens[2]).get()
        items = cache.get("node", "name = ", tokens[2])
        node = None
        
        if (len(items) == 1):
            node = items[0]
        
        if node == None :
            logging.error("Unsupported device " + tokens[2] + " in request " + s)           
            self.error(403)
            return
        
        if tokens[3] == "get":
            None
        else:
            if tokens[3] == "ack_on":
                logging.info("Device '%s' state was acked as ON" % tokens[2])
                node.on_state = True
            elif tokens[3] == "ack_off":
                logging.info("Device '%s' state was acked as OFF" % tokens[2])
                node.on_state = False
            else:
                logging.error("Unsupported state request " + tokens[2] + "in request " + s)
                return
   
            node.put()
            cache.invalidate()
        
        self.response.out.write(simplejson.dumps(node.on_state)) 
        
class CleanupHandler(webapp.RequestHandler):
    def get(self):
        db.delete(Queue.all())
        db.delete(Command.all())
        db.delete(Node.all())  

class SetupHandler(webapp.RequestHandler):
    def get(self):
        newNode = Node(address = int("0x0013a200403bc53a", 0), name = 'device1', on_state = False)
        newNode.put()
        Command(node = newNode, pin = 0, name = "on").put()  
        Command(node = newNode, pin = 1, name = "off").put()

        newNode2 = Node(address = int("0x0013a200403bc53b", 0), name = 'therm_west', on_state = False)
        newNode2.put()
        Command(node = newNode2, pin = 0, name = "on").put()  
        Command(node = newNode2, pin = 1, name = "off").put()
        
cache = CacheHandler()

def main():   
    # supported URLs:
    # /device/[device1|therm_west]/[on|off]
    # /queue/[device1|therm_west]/[all|clear]
    # /state/[device1|therm_west]/[ack_on|ack_off|get]

    application = webapp.WSGIApplication([
                                          ('/dev/.*', DeviceCommandHandler),
                                          ('/queue/.*',  QueueCommandHandler),
                                          ('/state/.*',  StateHandler),
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
