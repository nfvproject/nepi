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
import socket
from optparse import OptionParser, SUPPRESS_HELP

from ns3wrapper import NS3Wrapper

class NS3WrapperMessage:
    CREATE = "CREATE"
    INVOKE = "INVOKE"
    SET = "SET"
    GET = "GET"
    TRACE = "TRACE"
    START = "START"
    STOP = "STOP"
    SHUTDOWN = "SHUTDOWN"

def handle_message(ns3_wrapper, msg, args):
    if msg == NS3WrapperMessage.SHUTDOWN:
        ns3_wrapper.shutdown()
        return "BYEBYE"
    
    if msg == NS3WrapperMessage.STOP:
        time = None
        if args:
            time = args[0]

        ns3_wrapper.stop(time=time)
        return "STOPPED"

    if msg == NS3WrapperMessage.START:
        ns3_wrapper.start()
        return "STARTED"

    if msg == NS3WrapperMessage.CREATE:
        clazzname = args.pop(0)
        
        uuid = ns3_wrapper.create(clazzname, *args)
        return uuid

    if msg == NS3WrapperMessage.INVOKE:
        uuid = args.pop(0)
        operation = args.pop(0)
        
        uuid = ns3_wrapper.invoke(uuid, operation, *args)
        return uuid

    if msg == NS3WrapperMessage.GET:
        uuid = args.pop(0)
        name = args.pop(0)

        value = ns3_wrapper.get(uuid, name)
        return value

    if msg == NS3WrapperMessage.SET:
        uuid = args.pop(0)
        name = args.pop(0)
        value = args.pop(0)

        value = ns3_wrapper.set(uuid, name, value)
        return value
 
    if msg == NS3WrapperMessage.TRACE:
        return "NOT IMPLEMENTED"

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
 
    msg = ''.join(msg).split('\n')[0]

    # The message might have arguments that will be appended
    # as a '|' separated list after the message identifier
    def decode(arg):
        arg = base64.b64decode(arg).rstrip()
        return cPickle.loads(arg)

    dargs = map(decode, msg.split("|"))

    # decoded message
    dmsg = dargs.pop(0)

    return (dmsg, dargs)

def send_reply(conn, reply):
    encoded = base64.b64encode(cPickle.dumps(reply))
    conn.send("%s\n" % encoded)

def get_options():
    usage = ("usage: %prog -S <socket-name>")
    
    parser = OptionParser(usage = usage)

    parser.add_option("-S", "--socket-name", dest="socket_name",
        help = "Name for the unix socket used to interact with this process", 
        default = "tap.sock", type="str")

    (options, args) = parser.parse_args()
    
    return options.socket_name

def run_server(socket_name): 
    ns3_wrapper = NS3Wrapper()

    # create unix socket to receive instructions
    sock = create_socket(socket_name)
    sock.listen(0)

    # wait for messages to arrive and process them
    stop = False

    while not stop:
        conn, addr = sock.accept()
        conn.settimeout(5)

        try:
            (msg, args) = recv_msg(conn)
        except socket.timeout, e:
            # Ingore time-out
            continue

        if not msg:
            # Ignore - connection lost
            break
 
        ns3_wrapper.logger.debug("Message received %s args %s" % ( msg, str(args)))

        if msg == NS3WrapperMessage.SHUTDOWN:
           stop = True
   
        reply = handle_message(ns3_wrapper, msg, args)

        try:
            send_reply(conn, reply)
        except socket.error:
            break

if __name__ == '__main__':
            
    socket_name = get_options()

    run_server(socket_name)

