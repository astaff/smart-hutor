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
    
class Queue(db.Model):
    command = db.ReferenceProperty(reference_class = Command, collection_name= 'queue_instances')
    id = db.IntegerProperty()

class MainHandler(webapp.RequestHandler):
    def get(self):
        self.response.out.write('Hello world!!!')

class DeviceCommandHandler(webapp.RequestHandler):
    def get(self):
        s = self.request.path
        tokens = s.split('/')
        if len(tokens) < 4: 
            self.error(403)
            return 
            
        node = Node.all().filter('name =', tokens[2]).get()
        if node == None :
            self.error(403)
            return
        
        c = node.commands.filter('name =', tokens[3]).get()
        if c == None :
            self.error(403)
            return
        
        Queue(command = c).put()

class QueueCommandHandler(webapp.RequestHandler):
    def get(self):
        results = []
        for queue_item in Queue.all().run():
            results.append((queue_item.command.node.address, queue_item.command.pin))
          
        self.response.out.write(simplejson.dumps(results))

class QueueClearCommandHandler(webapp.RequestHandler):
    def get(self):
        db.delete(Queue.all())
        
class CleanupHandler(webapp.RequestHandler):
    def get(self):
        db.delete(Queue.all())
        db.delete(Command.all())
        db.delete(Node.all())  

class SetupHandler(webapp.RequestHandler):
    def get(self):
        newNode = Node(address = int("0x0013a200403bc53a", 0), name = 'device1')
        newNode.put()
        Command(node = newNode, pin = 0, name = "on").put()  
        Command(node = newNode, pin = 1, name = "off").put()

def main():   
    application = webapp.WSGIApplication([
                                          ('/dev/.*', DeviceCommandHandler),
                                          ('/queue/all', QueueCommandHandler),
                                          ('/queue/clear', QueueClearCommandHandler),
                                          ('/cleanup', CleanupHandler),
                                          ('/setup', SetupHandler)
                                          ],
                                     debug=True)
 
#    application = webapp.WSGIApplication([('/', MainHandler)],
#                                         debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
