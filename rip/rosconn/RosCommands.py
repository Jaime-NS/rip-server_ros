import sys
import time
import trace
import rospy
import psutil
import signal
import roslaunch
import threading
import subprocess
from importlib import import_module

class Roscore(object):
    """
    Class to start roscore
    """
    def __init__(self):
        pass

    def run(self):
        try:
            self.roscore_process = subprocess.Popen(['roscore'])
            self.roscore_pid = self.roscore_process.pid  # pid of the roscore process (which has child processes)
        except OSError as e:
            sys.stderr.write('roscore could not be run')
            raise e

    def terminate(self):
        print("try to kill child pids of roscore pid: " + str(self.roscore_pid))
        kill_child_processes(self.roscore_pid)
        self.roscore_process.terminate()
        self.roscore_process.wait()  # important to prevent from zombie process

    def kill_child_processes(parent_pid, sig=signal.SIGTERM):
        try:
            parent = psutil.Process(parent_pid)
            print(parent)
        except psutil.NoSuchProcess:
            print("parent process not existing")
            return
        children = parent.children(recursive=True)
        print(children)
        for process in children:
            print("try to kill child: " + str(process))
            process.send_signal(sig)


class Roslaunch(object):
    """
    Class to run a node (it also starts roscore if not already started)
    """
    def __init__(self, id):
        self.id = id

    def launch(self, package=None, executable=None, name=None):
        try:
            self.node = roslaunch.core.Node(package, executable, name)

            launch = roslaunch.scriptapi.ROSLaunch()
            launch.start()

            self.process = launch.launch(self.node)
        except:
            print "Node doesn't exist. Please, check the package and executable."

    def terminate(self):
        self.process.stop()


class Rospub(object):
    """
    Class to publish in an existing or new topic
    """
    def __init__(self):
        rospy.init_node('ripnode')

    def publish(self, topic, msgpackage, msgclass, value):
        data_class = getattr(import_module(msgpackage), msgclass)

        self.data = data_class()
        self.setValue(self.data, None, value)

        self.pub = rospy.Publisher(topic, data_class, queue_size=10)
        self.rate = rospy.Rate(10)
        init_time = rospy.get_time()

        while (rospy.get_time() - init_time < 0.25):
            self.pub.publish(self.data)
            self.rate.sleep()

    def setValue(self, obj, att, value):
        try:
            if not att == None:
                new_obj = eval("obj.%s" % att)
            else:
                new_obj = obj
            for a in new_obj.__slots__:
                self.setValue(new_obj, a, value[new_obj.__slots__.index(a)])

        except:
            setattr(obj, att, value)


class Rossub(object):
    """
    Class to subscribe to an existing topic
    """
    def __init__(self):
        self.sub = None
        self.data = None
        rospy.init_node('ripnode')

    def subscribe(self, topic, msgpackage, msgclass):
        data_class = getattr(import_module(msgpackage), msgclass)
        value = []
        self.sub = rospy.Subscriber(topic, data_class, self.callback, value)
        time.sleep(0.1)
        return value

    def callback(self, data, value):
        self.data = data
        value = self.getValue(self.data, None, value)
        self.sub.unregister()

    def getValue(self, obj, att, value):
        try:
            if not att == None:
                new_obj = eval("obj.%s" % att)
            else:
                new_obj = obj
            for a in new_obj.__slots__:
                self.getValue(new_obj, a, value)

        except:
            value.append(getattr(obj, att))
        return value


class Rosclient(object):
    """
    Class to create a client to call a service
    """
    def __init__(self):
        pass

    def call(self, srv, srvpackage, srvclass, args=None):
        data_class = getattr(import_module(srvpackage), srvclass)
        rospy.wait_for_service(srv)
        self.client = rospy.ServiceProxy(srv, data_class)
        if not args == "None":
            self.client(*args)
        else:
            self.client()


def RosGetParam(param):
    return rospy.get_param(param)


def RosSetParam(param, value):
    return rospy.set_param(param, value)


def Rosexec(code):
    try:
        exec(code)
    except:
        print "ERROR IN CODE"


class Rosthread(threading.Thread):
    """
    Class to create a threading
    """
    def __init__(self, *args, **keywords):
        threading.Thread.__init__(self, *args, **keywords)
        self.killed = False

    def start(self):
        self.__run_backup = self.run
        self.run = self.__run
        threading.Thread.start(self)

    def __run(self):
        sys.settrace(self.globaltrace)
        self.__run_backup()
        self.run = self.__run_backup

    def globaltrace(self, frame, event, arg):
        if event == 'call':
          return self.localtrace
        else:
          return None

    def localtrace(self, frame, event, arg):
        if self.killed:
          if event == 'line':
            raise SystemExit()
        return self.localtrace

    def kill(self):
        self.killed = True


def parallel_exec(code):
    try:
        print "thread created"
        exec(code)
    except:
        print "Error in code"
    print "thread done"
