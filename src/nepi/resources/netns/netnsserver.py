#
#    NEPI, a framework to manage network experiments
#    Copyright (C) 2014 INRIA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Author: Alina Quereilhac <alina.quereilhac@inria.fr>

import base64
import cPickle
import errno
import logging
import os
import socket
import sys

from optparse import OptionParser, SUPPRESS_HELP

from netnswrapper import NetNSWrapper

class NetNSWrapperMessage:
    CREATE = "CREATE"
    INVOKE = "INVOKE"
    SET = "SET"
    GET = "GET"
    FLUSH = "FLUSH"
    SHUTDOWN = "SHUTDOWN"

def handle_message(wrapper, msg_type, args, kwargs):
    if msg_type == NetNSWrapperMessage.SHUTDOWN:
        wrapper.shutdown()

        return "BYEBYE"
    
    if msg_type == NetNSWrapperMessage.CREATE:
        clazzname = args.pop(0)
        
        return wrapper.create(clazzname, *args)
        
    if msg_type == NetNSWrapperMessage.INVOKE:
        uuid = args.pop(0)
        operation = args.pop(0)
   
        return wrapper.invoke(uuid, operation, *args, **kwargs)

    if msg_type == NetNSWrapperMessage.GET:
        uuid = args.pop(0)
        name = args.pop(0)

        return wrapper.get(uuid, name)
        
    if msg_type == NetNSWrapperMessage.SET:
        uuid = args.pop(0)
        name = args.pop(0)
        value = args.pop(0)

        return wrapper.set(uuid, name, value)

    if msg_type == NetNSWrapperMessage.FLUSH:
        # Forces flushing output and error streams.
        # NS-3 output will stay unflushed until the program exits or 
        # explicit invocation flush is done
        sys.stdout.flush()
        sys.stderr.flush()

        wrapper.logger.debug("FLUSHED") 
        
        return "FLUSHED"

def create_socket(socket_name):
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.bind(socket_name)
    return sock

def recv_msg(conn):
    msg = []
    chunk = ''

    while '\n' not in chunk:
        try:
            chunk = conn.recv(1024)
        except (OSError, socket.error), e:
            if e[0] != errno.EINTR:
                raise
            # Ignore eintr errors
            continue

        if chunk:
            msg.append(chunk)
        else:
            # empty chunk = EOF
            break
 
    msg = ''.join(msg).strip()

    # The message is formatted as follows:
    #   MESSAGE_TYPE|args|kwargs
    #
    #   where MESSAGE_TYPE, args and kwargs are pickld and enoded in base64

    def decode(item):
        item = base64.b64decode(item).rstrip()
        return cPickle.loads(item)

    decoded = map(decode, msg.split("|"))

    # decoded message
    dmsg_type = decoded.pop(0)
    dargs = list(decoded.pop(0)) # transforming touple into list
    dkwargs = decoded.pop(0)

    return (dmsg_type, dargs, dkwargs)

def send_reply(conn, reply):
    encoded = base64.b64encode(cPickle.dumps(reply))
    conn.send("%s\n" % encoded)

def get_options():
    usage = ("usage: %prog -S <socket-name> -L <ns-log>  -D <enable-dump> -v ")
    
    parser = OptionParser(usage = usage)

    parser.add_option("-S", "--socket-name", dest="socket_name",
        help = "Name for the unix socket used to interact with this process", 
        default = "tap.sock", type="str")

    parser.add_option("-L", "--ns-log", dest="ns_log",
        help = "NS_LOG environmental variable to be set", 
        default = "", type="str")

    parser.add_option("-D", "--enable-dump", dest="enable_dump",
        help = "Enable dumping the remote executed ns-3 commands to a script "
            "in order to later reproduce and debug the experiment",
        action = "store_true",
        default = False)

    parser.add_option("-v", "--verbose",
        help="Print debug output",
        action="store_true", 
        dest="verbose", default=False)

    (options, args) = parser.parse_args()
    
    return (options.socket_name, options.verbose, options.ns_log,
            options.enable_dump)

def run_server(socket_name, level = logging.INFO, ns_log = None, 
        enable_dump = False):

    # Sets NS_LOG environmental variable for NS debugging
    if ns_log:
        os.environ["NS_LOG"] = ns_log

    ###### ns-3 wrapper instantiation

    wrapper = NetNSWrapper(loglevel=level, enable_dump = enable_dump)
    
    wrapper.logger.info("STARTING...")

    # create unix socket to receive instructions
    sock = create_socket(socket_name)
    sock.listen(0)

    # wait for messages to arrive and process them
    stop = False

    while not stop:
        conn, addr = sock.accept()
        conn.settimeout(5)

        try:
            (msg_type, args, kwargs) = recv_msg(conn)
        except socket.timeout, e:
            # Ingore time-out
            continue

        if not msg_type:
            # Ignore - connection lost
            break

        if msg_type == NetNSWrapperMessage.SHUTDOWN:
           stop = True
  
        try:
            reply = handle_message(wrapper, msg_type, args, kwargs)  
        except:
            import traceback
            err = traceback.format_exc()
            wrapper.logger.error(err) 
            raise

        try:
            send_reply(conn, reply)
        except socket.error:
            break
        
    wrapper.logger.info("EXITING...")

if __name__ == '__main__':
            
    (socket_name, verbose, ns_log, enable_dump) = get_options()

    ## configure logging
    FORMAT = "%(asctime)s %(name)s %(levelname)-4s %(message)s"
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(format = FORMAT, level = level)

    ## Run the server
    run_server(socket_name, level, ns_log, enable_dump)

