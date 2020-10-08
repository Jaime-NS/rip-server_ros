# - *- coding: utf- 8 - *-
"""
@author: jcsombria
"""
import cherrypy
import os
import socket
from rip.RIPGeneric import RIPGeneric
from rip.core import *


class HttpServer(object):
    """
    RIP Server implementation
    """
    exposed = True

    def __init__(self, control=RIPGeneric(), host='127.0.0.1', port=8080):
        self.control = control
        self.host = host
        self.port = port
        self.experiences = [{'id': control.name}]
        self.firstTime = False
        self.connectedClients = 0

    @cherrypy.expose
    def index(self, expId=None):
        """
        GET - Retrieve the list of experiences or information about a specific experience
        """
        if expId is not None:
            if expId in [e['id'] for e in self.experiences]:
                response = self.control.info(self.getAddr())
            else:
                response = '{}'
        else:
            response = self.info()
        return response.encode("utf-8")

    def getAddr(self):
        return '%s:%s' % (self.host, self.port)

    @cherrypy.expose
    def SSE(self, expId=None):
        """
        SSE - Connect to an experience's SSE channel to receive periodic updates
        """
        cherrypy.response.headers['Content-Type'] = 'text/event-stream'
        cherrypy.response.headers['Cache-Control'] = 'no-cache'
        cherrypy.response.headers['Connection'] = 'keep-alive'
        cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'
        if expId is not None:
            if expId in [e['id'] for e in self.experiences]:
                if not self.control.running:
                    self.control.start()
                return self.control.nextSample()
            return 'event: CLOSE\n\n'

    SSE._cp_config = {'response.stream': True}

    @cherrypy.expose
    @cherrypy.tools.accept(media='application/json')
    def POST(self):
        """
        POST - JSON-RPC control commands (get/set)
        """
        cherrypy.response.headers['Access-Control-Allow-Origin'] = '*'
        socket = cherrypy.request.body.fp
        message = socket.read()
        if not self.control.running:
            self.control.start()
        response = self.control.parse(message)
        return response.encode("utf-8")

    def info(self):
        """
        Build server info string
        """
        meta = RIPExperienceList(self.experiences, [self.buildGetInfo()])
        return str(meta)

    def buildGetInfo(self):
        return RIPMethod(
            url='%s/RIP' % self.getAddr(),
            description='Retrieves information (variables and methods) of the experiences in the server',
            type_='GET',
            params=[
                RIPParam(name='Accept', required='no', location='header', value='application/json'),
                RIPParam(name='expId', required='no', location='query', type_='string'),
            ],
            returns='application/json',
            example='http://%s/RIP?expId=%s' % (self.getAddr(), self.control.name)
        )

    def start(self, enable_ssl=False):
        base_dir = os.path.dirname(os.path.realpath(__file__))
        log_dir = os.path.join(base_dir, 'log')
        if not os.path.isdir(log_dir):
            os.mkdir(log_dir)
        access_log_file = os.path.join(log_dir, 'access.log')
        error_log_file = os.path.join(log_dir, 'error.log')
        cherrypy.config.update({
            'environment': 'production',
            'server.socket_host': '0.0.0.0',
            'server.thread_pool': 25,
            'server.socket_queue_size': 10,
            'engine.autoreload.on': False,
            'log.access_file': access_log_file,
            'log.errors_file': error_log_file
        })
        config = {
            '/': {
                'tools.response_headers.on': True,
                'tools.response_headers.headers': [
                  ('Content-Type', 'application/json'),
                  ('Access-Control-Allow-Origin', '*'),
                ],
                'tools.encode.on': True,
                'tools.encode.encoding': 'utf-8',
                # Avoid redirect when the URL does not have an ending '\'
                'tools.trailing_slash.on': False,
            },
        }
        if enable_ssl:
            cherrypy.server.ssl_module = 'builtin'
            cherrypy.server.ssl_certificate = '%s/%s' % (base_dir, 'cert.pem')
            cherrypy.server.ssl_private_key = '%s/%s' % (base_dir, 'privkey.pem')

        #ports = [self.port, self.port+1]  # add more ports if desired
        #for port in ports:
        #    print("Trying to start RIP in port " + str(self.port))
        #    self.port = port
        #    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #    try:
        #        cherrypy.config.update({'server.socket_port': self.port})
        #        s.bind((self.host, self.port))
        #        print("RIP is now running in " + self.getAddr())
        #        cherrypy.quickstart(self, '/RIP', config)
        #    except socket.error:
        #        print("RIP can not be started in " + self.getAddr())

        print("RIP is now running")
        cherrypy.quickstart(self, '/RIP', config)

    def stop(self):
        self.control.stop()

    def exit(self):
        self.control.exitThis()
        cherrypy.engine.exit()

# --------------------------------------------------------------------------------------------------


if __name__ == '__main__':
    HttpServer().start()
