"""
@author: jcsombria
"""
from jsonrpc.JsonRpcServer import JsonRpcServer
from jsonrpc.JsonRpcBuilder import JsonRpcBuilder
from rip.core.RIPMeta import *
import samplers
import signal

builder = JsonRpcBuilder()


class RIPGeneric(JsonRpcServer):
    """
    RIP Server - Reference Implementation
    """

    def __init__(self, info={}):
        """
        Constructor
        """
        metadata = self._parse_info(info)
        super(RIPGeneric, self).__init__(metadata['name'], metadata['description'])
        self.metadata = metadata
        self.samplingPeriod = 0.1
        self.sseSampling = 2  # Send data through SSE once every sseSampling samplings, given by samplingPeriod
        self.sseRunning = False
        self._running = False
        self.counter = -1
        self.addMethods({
            'get': {'description': 'To read server variables',
                    'params': {'expId': 'string', 'variables': '[string]'},
                    'implementation': self.get,
                    },
            'set': {'description': 'To write server variables',
                    'params': {'expId': 'string', 'variables': '[string]', 'values': '[]'},
                    'implementation': self.set,
                    },
        })
        signal.signal(signal.SIGINT, self.exitThis)

    def default_info(self):
        return {
            'name': 'RIP Generic',
            'description': 'Generic RIP Server Implementation.',
            'authors': 'J. Chacon',
            'keywords': 'Raspberry PI, RIP',
            'readables': [{
              'name': 'time',
              'description': 'Server time in seconds',
              'type': 'float',
              'min': '0',
              'max': 'Inf',
              'precision': '0',
            }],
            'writables': [],
        }

    def _parse_info(self, info):
        metadata = self.default_info()
        for p in info:
            try:
                metadata[p] = info[p]
            except:
                print('[WARNING] Property: %s not specified. Setting default value.' % p)
        return metadata

    def start(self):
        """
        Iniatilizes the server. Any code meant to be run at init should be here.
        """
        if not self.sseRunning:
            self.sseRunning = True
            self.sampler = samplers.Periodic(self.samplingPeriod)
        self._running = True

    @property
    def running(self):
        return self._running

    def info(self, address='127.0.0.1:8080'):
        """
        Retrieve the experience's info
        """
        try:
            info = self.info_string
        except:
            info = self.build_info(address)
            self.info_string = info
        return info

    def build_info(self, address):
        """
        Generate the experience's info string
        """
        info = RIPServerInfo(
            self.name,
            self.description,
            authors=self.metadata['authors'],
            keywords=self.metadata['keywords']
        )
        readables = RIPVariablesList(
            list_=self.metadata['readables'],
            methods=[self.buildSSEGetInfo(address), self.buildPOSTGetInfo(address)],
            read_notwrite=True
        )
        writables = RIPVariablesList(
            list_=self.metadata['writables'],
            methods=[self.buildPOSTSetInfo(address)],
            read_notwrite=False
        )
        meta = RIPMetadata(info, readables, writables)
        return str(meta)

    def buildSSEGetInfo(self, address):
        return RIPMethod(
            url='%s/RIP/SSE' % address,
            description='Suscribes to an SSE to get regular updates on the servers\' variables',
            type_='GET',
            params=[
                RIPParam(name='Accept', required='no', location='header', value='application/json'),
                RIPParam(name='expId', required='yes', location='query', type_='string'),
                RIPParam(name='variables', required='no', location='query', type_='array', subtype='string'),
            ],
            returns='text/event-stream',
            example='%s/RIP/SSE?expId=%s' % (address, self.metadata['name']),
        )

    def buildPOSTGetInfo(self, address):
        elements = [{'description': 'Experience id', 'type': 'string'},
                    {'description': 'Name of variables to be retrieved', 'type': 'array', 'subtype': 'string'}]
        return RIPMethod(
            url='%s/RIP/POST' % address,
            description='Sends a request to retrieve the value of one or more servers\' variables on demand',
            type_='POST',
            params=[
                RIPParam(name='Accept', required='no', location='header', value='application/json'),
                RIPParam(name='Content-Type', required='yes', location='header', type_='application/json'),
                RIPParam(name='jsonrpc', required='yes', type_='string', location='body', value='2.0'),
                RIPParam(name='method', required='yes', type_='string', location='body', value='get'),
                RIPParam(name='params', required='yes', type_='array', location='body', elements=elements),
                RIPParam(name='id', required='yes', type_='int', location='body'),
            ],
            returns='application/json',
            example={'%s/RIP/POST' % address: {
                'headers': {'Accept': 'application/json', 'Content-Type': 'application/json'},
                'body': {'jsonrpc': '2.0', 'method': 'get', 'params': ['%s' % self.metadata['name'], [r['name'] for r in
                          self.metadata['readables']]], 'id': '1'}
            }}
        )

    def buildPOSTSetInfo(self, address):
        elements = [{'description': 'Experience id', 'type': 'string'},
                    {'description': 'Name of variables to write', 'type': 'array', 'subtype': 'string'},
                    {'description': 'Value for variables', 'type': 'array', 'subtype': 'mixed'}]
        params_post_set = [
            RIPParam(name='Accept', required='no', location='header', value='application/json'),
            RIPParam(name='Content-Type', required='yes', location='header', type_='application/json'),
            RIPParam(name='jsonrpc', required='yes', type_='string', location='body', value='2.0'),
            RIPParam(name='method', required='yes', type_='string', location='body', value='set'),
            RIPParam(name='params', required='yes', type_='array', location='body', elements=elements),
            RIPParam(name='id', required='yes', type_='int', location='body'),
            RIPParam(name='variables', required='no', location='query', type_='array', subtype='string'),
        ]
        example_post_set = {
            '%s/RIP/POST' % address: {
                'headers': {'Accept': 'application/json', 'Content-Type': 'application/json'},
                'body': {'jsonrpc': '2.0', 'method': 'set', 'params': ['%s' % self.metadata['name'], [w['name'] for w in
                          self.metadata['writables']], ['val' for w in self.metadata['writables']]], 'id': '1'}
            }
        }
        return RIPMethod(
            url='%s/RIP/POST' % address,
            description='Sends a request to retrieve the value of one or more servers\' variables on demand',
            type_='POST',
            params=params_post_set,
            returns='application/json',
            example=example_post_set
        )

    def set(self, expid, variables, values):
        """
        Sends one or more variables to the server
        """
        pass

    def get(self, expid, variables):
        """
        Retrieve one or more variables from the server
        """
        pass

    def stop(self):
        """
        Stop processes
        """
        pass

    def exitThis(self):
        """
        Close processes
        """
        pass

    def _getReadables(self):
        readables = []
        for r in self.metadata['readables']:
            readables.append(r['name'])
        return readables

    def _getWritables(self):
        writables = []
        for r in self.metadata['writables']:
            writables.append(r['name'])
        return writables

    def nextSample(self):
        """
        Retrieve the next periodic update
        """
        self.beforeRun()
        self.start()

        while self.sseRunning:
            self.sampler.wait()
            try:
                self.preGetValuesToNotify()
                toReturn = self.getValuesToNotify()
                self.postGetValuesToNotify()
            except:
                toReturn = 'ERROR'
            self.counter = self.counter + 1
            if self.counter % self.sseSampling == 0:
                try:
                    event = 'periodiclabdata'
                    id = round(self.sampler.time * 1000)
                    yield 'event: %s\nid: %s\ndata: %s\n\n' % (event, id, ujson.dumps({"result": toReturn}))
                except:
                    self._running = False
                    self.sseRunning = False
                    self.stop()
                    print("Control stopped")

    def beforeRun(self):
        """
        To do before obtaining values to notify
        """
        pass

    def preGetValuesToNotify(self):
        """
        To do before obtaining values to notify
        """
        pass

    def getValuesToNotify(self):
        """
        Which values will be notified
        """
        pass

    def postGetValuesToNotify(self):
        """
        To do after obtaining values to notify
        """
        pass
