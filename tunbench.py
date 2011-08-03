import os
import sys
import threading
import time
import cProfile
import pstats

from nepi.util import tunchannel

remote = open("/dev/zero","r+b")
tun = open("/dev/zero","r+b")

def rwrite(remote, packet, remote_fd = remote.fileno(), os_write=os.write, len=len):
    global bytes
    bytes += len(packet)
    return os_write(remote_fd, packet)

def rread(remote, maxlen, remote_fd = remote.fileno(), os_read=os.read):
    global bytes
    rv = os_read(remote_fd, maxlen)
    bytes += len(rv)
    return rv

def test(cipher, passphrase):
   TERMINATE = []
   def stopme():
       time.sleep(100)
       TERMINATE.append(None)
   t = threading.Thread(target=stopme)
   t.start()
   tunchannel.tun_fwd(tun, remote, True, True, passphrase, True, TERMINATE, None, tunkqueue=500,
        rwrite = rwrite, rread = rread, cipher=cipher)

# Swallow exceptions on decryption
def decrypt(packet, crypter, super=tunchannel.decrypt):
    try:
        return super(packet, crypter)
    except:
        return packet
tunchannel.decrypt = decrypt

for cipher in (None, 'AES', 'Blowfish', 'DES', 'DES3'):
    if cipher is None:
        passphrase = None
    else:
        passphrase = 'Abracadabra'
    bytes = 0
    cProfile.runctx('test(%r,%r)' % (cipher, passphrase),globals(),locals(),'tunchannel.%s.profile' % (cipher,))
    
    print "Profile (%s):" % ( cipher, )
    pstats.Stats('tunchannel.%s.profile' % cipher).strip_dirs().sort_stats('time').print_stats()
    
    print "Bandwidth (%s): %.4fMb/s" % ( cipher, bytes / 200.0 * 8 / 2**20, )


