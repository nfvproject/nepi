#!/usr/bin/env python

from nepi.util import tunchannel
import socket
import time
import threading
import unittest

class TunnChannelTestCase(unittest.TestCase):
    def test_send_suspend_terminate(self):
        def tun_fwd(local, remote, TERMINATE, SUSPEND, STOPPED):
            tunchannel.tun_fwd(local, remote, True, True, None, True,
                TERMINATE, SUSPEND, None)
            STOPPED.append(None)
    
        TERMINATE = []
        SUSPEND = []
        STOPPED = []
    
        s1, s2 = socket.socketpair()
        s3, s4 = socket.socketpair()
        s4.settimeout(2.0)

        t = threading.Thread(target=tun_fwd, args=[s2, s3, TERMINATE, SUSPEND, STOPPED])
        t.start()

        txt = "0000|received"
        s1.send(txt)
        rtxt = s4.recv(len(txt))

        self.assertTrue(rtxt == txt[4:])
        
        # Let's try to suspend execution now
        cond = threading.Condition()
        SUSPEND.insert(0, cond)

        txt = "0000|suspended"
        s1.send(txt)
        
        rtxt = "timeout"
        try:
            rtxt = s4.recv(len(txt))
        except socket.timeout:
            pass
                    
        self.assertTrue(rtxt == "timeout")

        # Let's see if we can resume and receive the message
        cond = SUSPEND[0]
        SUSPEND.remove(cond)
        cond.acquire()
        cond.notify()
        cond.release()

        rtxt = s4.recv(len(txt))
        self.assertTrue(rtxt == txt[4:])
              
        # Stop forwarding         
        TERMINATE.append(None)

        txt = "0000|never received"
        s1.send(txt)
        
        rtxt = "timeout"
        try:
            rtxt = s4.recv(len(txt))
        except socket.timeout:
            pass
                    
        self.assertTrue(rtxt == "timeout")
        self.assertTrue(STOPPED)

if __name__ == '__main__':
    unittest.main()

