
import logging
import os
import weakref 

from nepi.execute import controllers
form nepi.testbeds.planetlab.design import boxes 

class NetnsElement(object):
    def __init__(self, guid, box_id, attributes, tc):
        super(Node, self).__init__()
        self._guid = guid
        self._box_id = box_id
        self._attributes = attributes 
        self._tc = tc
        self._element = None
        self._node_guid = None
        self._state = ResourceState.CREATED

    @property
    def box_id(self):
        return self._box_id

    @property
    def guid(self):
        return self._guid

    @property
    def tc(self):
        return None if self._tc else self._tc()
 
    @property
    def netns(self):
        return self.tc.netns

    @property
    def element(self):
        return self._element

    @property
    def node_guid(self):
        return self._node_guid

    def connect(self, connector, other_guid, other_box_id, other_connector,
            **kwargs):
        return (controllers.EventStatus.SUCCESS, "")

    def postconnect(self, connector, other_guid, other_box_id, other_connector,
            **kwargs):
        return (controllers.EventStatus.SUCCESS, "")

    def start(self):
        return (controllers.EventStatus.SUCCESS, "")

    def stop(self):
        return (controllers.EventStatus.SUCCESS, "")

    def status(self):
        status = self._status
        return (controllers.EventStatus.SUCCESS, status)

    def get(self, attr):
        if self.element and hasattr(self.element, attr):
            value = getattr(self.element, attr)
        elif attr in self._attributes:
            value = self._attributes[attr]
        else:
            self.tc._logger.debug("get(): Invalid attribute %s for %s.guid(%d)" %
                    (attr, self.box_id, self.guid))
            return (controllers.EventStatus.FAIL, "") 
        return (controllers.EventStatus.SUCCESS, value)

    def set(self, attr, value):
        if self.element and hasattr(self.element, attr):
            setattr(self.element, attr, value)
        elif attr in self._attributes:
            self._attributes[attr] = value
        else:
            self.tc._logger.debug("set(): Invalid attribute %s for %s.guid(%d)" % 
                    (attr, self.box_id, self.guid))
            return (controllers.EventStatus.FAIL, "") 
        return (controllers.EventStatus.SUCCESS, value)


class Node(NetnsElement):
    def __init__(self, guid, box_id, attributes, tc):
        super(Node, self).__init__(guid, box_id, attributes, tc)
        forward_X11 = attributes.get("forwardX11", False)
        self._element = self.netns.Node(forwardX11 = forwardX11)


class P2PInterface(NetnsElement):
    def __init__(self, guid, box_id, attributes, tc):
        super(P2PInterface, self).__init__(guid, box_id, attributes, tc)

    def connect(self, connector, other_guid, other_box_id, other_connector,
            **kwargs):
        status = controllers.EventStatus.SUCCESS
        result = ""

        if other_box_id not in [boxes.NODE, boxes.P2PIFACE]:
            self.tc._logger.debug("connect(): Invalid box_id %s for %s" %
                    (other_box_id, self.box_id) )
            return (controllers.EventStatus.FAIL, "") 

        other = self.tc.elements(other_guid)
        if not other:
            # Needs to wait until the other element is created
            return (controllers.EventStatus.RETRY, "") 

        if other_box_id == boxes.NODE:
            if not self.node_guid:
                self._node_guid = other_guid
        elif other_box_id == boxes.P2PIFACE:
            if not self.node_guid or not other.node_guid:
                # Needs to wait until both node_guids are set
                status = controllers.EventStatus.RETRY
                result = None
            elif not self.element and not other.element:
                node1 = self.tc.element(self.node_guid)
                node2 = self.tc.element(other.node_guid)
                self._element, other._element = self.netns.P2PInterface.create_pair(
                        node1, node2)

        return (status, result)


class TAPInterface(NetnsElement):
    def __init__(self, guid, box_id, attributes, tc):
        super(TAPInterface, self).__init__(guid, box_id, attributes, tc)

    def connect(self, connector, other_guid, other_box_id, other_connector,
            **kwargs):
        status = controllers.EventStatus.SUCCESS
        result = ""

        if other_box_id != boxes.NODE or other_connector != "->fd":
            self.tc._logger.debug("connect(): Invalid box_id %s for %s" %
                    (other_box_id, self.box_id) )
            return (controllers.EventStatus.FAIL, "") 
        
        if other_box_id == boxes.NODE:
            other = self.tc.elements(other_guid)
            if not other:
                # Needs to wait until the other element is created
                return (controllers.EventStatus.RETRY, "") 

            if not self._node_guid:
                other = self.tc.elements(other_guid)
                if not other:
                    self._logger.debug("connect(): Nonexistent element guid(%d)" % guid)
                    return (controllers.EventStatus.FAIL, "")

                self.node_guid = other.guid
                node = self.tc.element(self.node_guid)
                self._element = node.add_tap()

        elif other_connector == "fd->":
            if not "tun_addr" in kwargs:
                result = "kwargs:tun_addr:guid(%d).tun_addr" % other_guid
                return (controllers.EventStatus.RETRY, result)

            address = kwargs["tun_addr"]
            import passfd
            import socket
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
            sock.connect(address)
            passfd.sendfd(sock, self.element.fd, '0')
            # TODO: after succesful transfer, the tap device should close the fd

        return (status, result)


class TUNInterface(NetnsElement):
    def __init__(self, guid, box_id, attributes, tc):
        super(TUNInterface, self).__init__(guid, box_id, attributes, tc)

    def connect(self, connector, other_guid, other_box_id, other_connector,
            **kwargs):
        status = controllers.EventStatus.SUCCESS
        result = ""

        if other.box_id == boxes.NODE:
            if not self.node_guid:
                self.node_guid = other.guid
                node = self.tc.element(self.node_guid)
                self._element = node.add_tun()

        return (status, result)


class NodeInterface(NetnsElement):
    def __init__(self, guid, box_id, attributes, tc):
        super(NodeInterface, self).__init__(guid, box_id, attributes, tc)

    def connect(self, connector, other_guid, other_box_id, other_connector,
            **kwargs):
        status = controllers.EventStatus.SUCCESS
        result = ""

        if other.box_id == boxes.NODE:
            if not self.node_guid:
                self.node_guid = other.guid
                node = self.tc.element(self.node_guid)
                self._element = node.add_if()

        return (status, result)


class Switch(NetnsElement):
    def __init__(self, guid, box_id, attributes, tc):
        super(Switch, self).__init__(guid, box_id, attributes, tc)
        self._element = self.netns.Switch()

    def connect(self, connector, other_guid, other_box_id, other_connector,
            **kwargs):
        status = controllers.EventStatus.SUCCESS
        result = ""

        if other.box_id == boxes.NODEIFACE:
            if not self.element:
                # Needs to wait until element is created
                status = controllers.EventStatus.RETRY
                result = None
            else:
                self.element.connect(other.element)

        return (status, result)


class Application(NetnsElement):
    def __init__(self, guid, box_id, attributes, tc):
        super(Application, self).__init__(guid, box_id, attributes, tc)


class Trace(NetnsElement):
    def __init__(self, guid, box_id, attributes, tc):
        super(Trace, self).__init__(guid, box_id, attributes, tc)

    def trace_filepath(self, guid, filename = None):
        filename = "%d.trace" % guid
        return os.path.join(self.home_directory, filename)


class Route(NetnsElement):
    def __init__(self, guid, box_id, attributes, tc):
        super(Route, self).__init__(guid, box_id, attributes, tc)


class IP4Address(NetnsElement):
    def __init__(self, guid, box_id, attributes, tc):
        super(IP4Address, self).__init__(guid, box_id, attributes, tc)

class TunChannel(NetnsElement):
    def __init__(self, guid, box_id, attributes, tc):
        super(TunChannel, self).__init__(guid, box_id, attributes, tc)


class TestbedController(controllers.TestbedController):
    box_id2classes = dict({
        boxes.NODE: Node,
        boxes.P2PIFACE: P2PInterface,
        boxes.TAPIFACE: TAPInterface,
        boxes.TUNIFACE: TunInterface,
        boxes.NODEIFACE: NodeInterface,
        boxes.SWITCH: Switch,
        boxes.APPLICATION: Application,
        boxes.TUNCHANNEL: TunChannel,
        boxes.PCAPTRACE: Trace,
        boxes.OUTTRACE: Trace,
        boxes.ERRTRACE: Trace,
        boxes.ROUTE: Route, 
        boxes.IP4ADDRESS: IP4Address
     })

    class HostLock(object):
        # This class is used as a lock to prevent concurrency issues with more
        # than one instance of netns running in the same machine. Both in 
        # different processes or different threads.
        taken = False
        processcond = threading.Condition()
        
        def __init__(self, lockfile):
            processcond = self.__class__.processcond
            
            processcond.acquire()
            try:
                # It's not reentrant
                while self.__class__.taken:
                    processcond.wait()
                self.__class__.taken = True
            finally:
                processcond.release()
            
            self.lockfile = lockfile
            fcntl.flock(self.lockfile, fcntl.LOCK_EX)
        
        def __del__(self):
            processcond = self.__class__.processcond
            
            processcond.acquire()
            try:
                assert self.__class__.taken, "HostLock unlocked without being locked!"

                fcntl.flock(self.lockfile, fcntl.LOCK_UN)
                
                # It's not reentrant
                self.__class__.taken = False
                processcond.notify()
            finally:
                processcond.release()

     def __init__(self, guid, attributes):
        super(TestbedController, self).__init__(guid, attributes)
        self._netns = None
        self._elements = dict()
        self.__lock = open("/tmp/nepi-netns-lock", "a")
        self._home_dir = None
        self._logger = logging.getLogger("nepi.execute.tc.netns")

        self._setup()

    @property
    def netns(self):
        return self._netns

    def element(self, guid):
        return self._elements.get(guid)

    def recover(self):
        raise NotImplementedError

    def shutdown(self):
        status = controllers.EventStatus.SUCCESS
        result = ""

        try:
            for guid, elem in self._elements.iteritems():
                if isinstance(element, TunChannel):
                    elem.cleanup()
                elif isinstance(element, Trace):
                    elem.close()
                else:
                    if elem.box_id == boxes.NODE:
                        elem.destroy()
            self._elements.clear()
        except:
            status = controllers.EventStatus.FAIL
            import traceback
            result = traceback.format_exc()

        self._state = controllers.ResourceState.SHUTDOWN
        return (status, result)

    def create(self, guid, box_id, attributes):
        lock = self._lock()
        eClass = self.box_id2classes.get(box_id)
        if not eClass:
            self._logger.debug("create(): Unsupported box_id %s" % box_id)
            return (controllers.EventStatus.FAIL, "")
        tc = weakref.ref(self)
        elem = eClass(guid, box_id, attributes, tc)
        self._elements[guid] = elem
        return (controllers.EventStatus.SUCCESS, "")

    def connect(self, connector, other_guid, other_box_id, other_connector,
            **kwargs):
        elem = self.elements(guid)
        if not elem:
            self._logger.debug("connect(): Nonexistent element guid(%d)" % guid)
            return (controllers.EventStatus.FAIL, "")
        return elem.connect(connector, other_guid, other_box_id, other_connector,
                **kwargs) 

    def postconnect(self, connector, other_guid, other_box_id, other_connector, 
            **kwargs):
        elem = self.elements(guid)
        if not elem:
            self._logger.debug("postconnect(): Nonexistent element guid(%d)" % guid)
            return (controllers.EventStatus.FAIL, "")
        return elem.postconnect(connector, other_guid, other_box_id, other_connector,
                **kwargs) 

    def start(self, guid):
        if guid == self.guid:
            elements = self._elements.values()
        else:
            elem = self.elements(guid)
            if not elem:
                self._logger.debug("start(): Nonexistent element guid(%d)" % guid)
                return (controllers.EventStatus.FAIL, "")
            elements = [elem]

        for elem in elements:
            (status, result) = elem.start()
            if status != controllers.EventStatus.SUCCCESS:
                return (status, result)

        self._state = controllers.ResourceState.STARTED
        self._start_time = controller.strfnow()
        return (controllers.EventStatus.SUCCESS, "")

    def stop(self, guid):
        if guid == self.guid:
            elements = self._elements.values()
        else:
            elem = self.elements(guid)
            if not elem:
                self._logger.debug("stop(): Nonexistent element guid(%d)" % guid)
                return (controllers.EventStatus.FAIL, "")
            elements = [elem]

        for elem in elements:
            (status, result) = elem.stop()
            if status != controllers.EventStatus.SUCCCESS:
                return (status, result)

        self._state = controllers.ResourceState.STOPPED
        self._stop_time = controller.strfnow()
        return (controllers.EventStatus.SUCCESS, "")

    def set(self, guid, attr, value):
        if guid == self.guid:
            if attr in self._attributes:
                self._attributes[attr] = value
                return (controllers.EventStatus.SUCCESS, value)
            else:
                self._logger.debug("set(): Invalid attribute %s for element guid(%d)" % 
                        (attr, self.guid))
                return (controllers.EventStatus.FAIL, "")

        elem = self.elements(guid)
        if not elem:
            self._logger.debug("set(): Nonexistent element guid(%d)" % guid)
            return (controllers.EventStatus.FAIL, "")
        return elem.set(attr, value)

    def get(self, guid, attr):
        if guid == self.guid:
            if attr in self._attributes:
                value = self._attributes[attr]
                return (controllers.EventStatus.SUCCESS, value)
            else:
                self._logger.debug("get(): Invalid attribute %s for element guid(%d)" % 
                        (attr, self.guid))
                return (controllers.EventStatus.FAIL, "")

        elem = self.elements(guid)
        if not elem:
            self._logger.debug("get(): Nonexistent element guid(%d)" % guid)
            return (controllers.EventStatus.FAIL, "")
        return elem.get(attr)

    def state(self, guid):
        if guid == self.guid:
            state = self._state
            return (controllers.EventStatus.SUCCESS, state)

        elem = self.elements(guid)
        if not elem:
            self._logger.debug("state(): Nonexistent element guid(%d)" % guid)
            return (controllers.EventStatus.FAIL, "")
        return elem.state()

    def _lock(self):
        return self.HostLock(self.__lock)

    def _setup(self):
        self._home_dir = self._attributes["homeDirectory"]
        # create home...
        home = os.path.normpath(self.home_dir)
        if not os.path.exists(home):
            os.makedirs(home, 0755)

        self._netns = self._load_netns_module()
    
    def _load_netns_module(self):
        # TODO: Do something with the configuration!!!
        import sys
        __import__("netns")
        netns_mod = sys.modules["netns"]
        # enable debug
        debug = self._attributes.get("enableDebug", False)
        if debug:
            netns_mod.environ.set_log_level(netns_mod.environ.LOG_DEBUG)
        return netns_mod


TC_CLASS = TestbedController
TC_BOX_ID = EMULATION


