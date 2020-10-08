"""
@author: jnieto
"""
from rip.RIPGeneric import RIPGeneric
from rip.rosconn.RosCommands import *
import rosgraph
import json


class RIPRos(RIPGeneric):
    """
    RIP ROS Adapter
    """
    def __init__(self, info):
        """
        Constructor
        """
        super(RIPRos, self).__init__(info)
        if not rosgraph.is_master_online():
            self.roscore = Roscore()
            self.roscore.run()
        else:
            print "Roscore already running"

        self.rosnode = []
        try:
            package = self.metadata['model'].get('package')
            node = self.metadata['model'].get('node')
            node_name = self.metadata['model'].get('nodename')
            self.rosnode.append(Roslaunch(node_name))
            self.rosnode[0].launch(package, node, node_name)
        except:
            pass

        self.publisher = Rospub()
        self.subscriber = Rossub()
        self.client = Rosclient()
        self.code = ''
        self.proc = []


    def default_info(self):
        """
        Default metadata.
        """
        return {
            'name': 'ROS',
            'description': 'An implementation of RIP to control ROS',
            'authors': 'J. Nieto',
            'keywords': 'ROS',
            'readables': [],
            'writables': [],
        }


    def set(self, expid, variables, values):
        writables = self.metadata['writables']
        if isinstance(variables, list):
            for i in variables:
                for j in writables:
                    if j.get('name') == i:

                        if j['ros'].get('type') == 'node':
                            print "Starting/Terminating node"
                            package = j['ros'].get('package')
                            node = j['ros'].get('node')
                            node_name = j['ros'].get('nodename')
                            if values[variables.index(i)] == 1:
                                self.rosnode.append(Roslaunch(node_name))
                                for n in self.rosnode:
                                    if n.id == node_name:
                                        n.launch(package, node, node_name)
                                        break
                            elif values[variables.index(i)] == 0:
                                for n in self.rosnode:
                                    if n.id == node_name:
                                        n.terminate()
                                        del self.rosnode[self.rosnode.index(n)]
                                        break

                        elif j['ros'].get('type') == 'topic':
                            print "Sending msg to topic"
                            topic = j['ros'].get('topic')
                            msgpackage = j['ros'].get('msgpackage')
                            msgclass = j['ros'].get('msgclass')
                            self.publisher.publish(topic, msgpackage, msgclass, values[variables.index(i)])

                        elif j['ros'].get('type') == 'service':
                            print "Sending srv"
                            srv = j['ros'].get('srv')
                            srvpackage = j['ros'].get('srvpackage')
                            srvclass = j['ros'].get('srvclass')
                            self.client.call(srv, srvpackage, srvclass, values[variables.index(i)])

                        elif j['ros'].get('type') == 'param':
                            print "Sending param"
                            param = j['ros'].get('param')
                            RosSetParam(param, values[variables.index(i)])

                        elif j['ros'].get('type') == 'code':
                            print "Sending code"
                            self.code = values[variables.index(i)];
                            print self.code
                            try:
                                if self.proc.isAlive():
                                    self.proc.kill()
                                    self.proc.join()
                                    print "It was certainly alive"
                                else:
                                    print "The process was already dead"
                            except:
                                print "No process at all"

                            try:
                                self.proc = Rosthread(target=parallel_exec, args=(self.code,))
                                self.proc.daemon = True
                                self.proc.start()
                            except:
                                print "Error creating thread"
        """
        else:
            print "notisisntance"
            for j in writables:
                if j.get('name') == variables:

                    if j['ros'].get('type') == 'node':
                        print "Starting/Terminating node"
                        package = j['ros'].get('package')
                        node = j['ros'].get('node')
                        node_name = j['ros'].get('nodename')
                        if values[0] == 1:
                            self.rosnode.append(Roslaunch(node_name))
                            for n in self.rosnode:
                                if n.id == node_name:
                                    n.launch(package, node, node_name)
                                    break
                        elif values[0] == 0:
                            for n in self.rosnode:
                                if n.id == node_name:
                                    n.terminate()
                                    del self.rosnode[self.rosnode.index(n)]
                                    break

                    elif j['ros'].get('type') == 'topic':
                        topic = j['ros'].get('topic')
                        msgpackage = j['ros'].get('msgpackage')
                        msgclass = j['ros'].get('msgclass')
                        self.publisher.publish(topic, msgpackage, msgclass, values[0])

                    elif j['ros'].get('type') == 'service':
                        srv = j['ros'].get('srv')
                        srvpackage = j['ros'].get('srvpackage')
                        srvclass = j['ros'].get('srvclass')
                        self.client.call(srv, srvpackage, srvclass, values[0])

                    elif j['ros'].get('type') == 'param':
                        param = j['ros'].get('param')
                        RosSetParam(param, values[0])

                    elif j['ros'].get('type') == 'code':
                        self.code = values[0];
                        exec(self.code)
        #"""


    def get(self, expid, variables):
        readables = self.metadata['readables']
        values = []
        if isinstance(variables, list):
            for i in variables:
                for j in readables:
                    if j.get('name') == i:

                        if j['ros'].get('type') == 'topic':
                            topic = j['ros'].get('topic')
                            msgpackage = j['ros'].get('msgpackage')
                            msgclass = j['ros'].get('msgclass')
                            v = self.subscriber.subscribe(topic, msgpackage, msgclass)
                            values.append(v)

                        elif j['ros'].get('type') == 'param':
                            param = j['ros'].get('param')
                            v = RosGetParam(param)
                            values.append(v)
        """
        else:
            for j in readables:
                if j.get('name') == variables:

                    if j['ros'].get('type') == 'topic':
                        topic = j['ros'].get('topic')
                        msgpackage = j['ros'].get('msgpackage')
                        msgclass = j['ros'].get('msgclass')
                        v = self.subscriber.subscribe(topic, msgpackage, msgclass)
                        values.append(v)

                    elif j['ros'].get('type') == 'param':
                        param = j['ros'].get('param')
                        v = RosGetParam(param)
                        values.append(v)
        """
        print values
        return [variables, values]


    def preGetValuesToNotify(self):
        pass


    def getValuesToNotify(self, expid=None):
        values = self.get(expid, self._getReadables())
        return values


    def postGetValuesToNotify(self):
        pass


    def exitThis(self):
        self.roscore.terminate()
        for n in self.rosnode:
            n.terminate()
