#
#    NEPI, a framework to manage network experiments
#    Copyright (C) 2013 INRIA
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
#         Julien Tribino <julien.tribino@inria.fr>


import time
import hashlib
import threading

from nepi.resources.omf.omf5_api import OMF5API
from nepi.resources.omf.omf6_api import OMF6API

class OMFAPIFactory(object):
    """ 
    .. note::

        It allows the different RM to use the same xmpp client if they use 
        the same credentials.  For the moment, it is focused on XMPP.

    """
    # use lock to avoid concurrent access to the Api list at the same times by 2 
    # different threads
    lock = threading.Lock()
    _apis = dict()

    @classmethod 
    def get_api(cls, version, server, user, port, password, exp_id = None):
        """ Get an OMF Api

        :param version: OMF Version. Either 5 or 6
        :type version: str
        :param server: Xmpp Server Adress
        :type server: str
        :param user: Xmpp User
        :type user: str
        :param port: Xmpp Port (Default : 5222)
        :type port: str
        :param password: Xmpp Password
        :type password: str
        :param exp_id: Id of the experiment
        :type exp_id: str

        """
        if version and user and server and port and password:
            key = cls._make_key(version, server, user, port, password, exp_id)
            cls.lock.acquire()
            if key in cls._apis:
                #print "Api Counter : " + str(cls._apis[key]['cnt'])
                cls._apis[key]['cnt'] += 1
                cls.lock.release()
                return cls._apis[key]['api']
            else :
                omf_api = cls.create_api(version, server, user, port, password, exp_id)
                cls.lock.release()
                return omf_api
        return None

    @classmethod 
    def create_api(cls, version, server, user, port, password, exp_id):
        """ Create an OMF API if this one doesn't exist yet with this credentials

        :param version: OMF Version. Either 5 or 6
        :type version: str
        :param server: Xmpp Server Adress
        :type server: str
        :param user: Xmpp User
        :type user: str
        :param port: Xmpp Port (Default : 5222)
        :type port: str
        :param password: Xmpp Password
        :type password: str
        :param exp_id: Id of the experiment
        :type exp_id: str

        """
        key = cls._make_key(version, server, user, port, password, exp_id)
        if version == "5":
            omf_api = OMF5API(server, user, port, password, exp_id = exp_id)
        else :
            omf_api = OMF6API(server, user = user, port = port, password = password, exp_id = exp_id)
        cls._apis[key] = {}
        cls._apis[key]['api'] = omf_api
        cls._apis[key]['cnt'] = 1
        return omf_api

    @classmethod 
    def release_api(cls, version, server, user, port, password, exp_id = None):
        """ Release an OMF API with this credentials

        :param version: OMF Version. Either 5 or 6
        :type version: str
        :param server: Xmpp Server Adress
        :type server: str
        :param user: Xmpp User
        :type user: str
        :param port: Xmpp Port (Default : 5222)
        :type port: str
        :param password: Xmpp Password
        :type password: str
        :param exp_id: Id of the experiment
        :type exp_id: str

        """
        if version and user and server and port and password:
            key = cls._make_key(version, server, user, port, password, exp_id)
            if key in cls._apis:
                cls._apis[key]['cnt'] -= 1
                #print "Api Counter : " + str(cls._apis[key]['cnt'])
                if cls._apis[key]['cnt'] == 0:
                    omf_api = cls._apis[key]['api']
                    omf_api.disconnect()


    @classmethod 
    def _make_key(cls, *args):
        """ Hash the credentials in order to create a key

        :param args: list of arguments used to create the hash (server, user, port, ...)
        :type args: list

        """
        skey = "".join(map(str, args))
        return hashlib.md5(skey).hexdigest()



