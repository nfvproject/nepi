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


import hashlib
import threading


class NewAPIFactory(object):
    """ 
        Class for the new Api Factoy

    """
    # use lock to avoid concurrent access to the Api list at the same times by 2 
    # different threads
    lock = threading.Lock()
    _apis = dict()

    @classmethod 
    def get_api(cls, cred1, cred2):
        """ Get an instance of the API depending on the credentials

        """
        if cred1 and cred2:
            key = cls._make_key(cred1,cred2)
            cls.lock.acquire()
            if key in cls._apis:
                cls._apis[key]['cnt'] += 1
                cls.lock.release()
                return cls._apis[key]['api']
            else :
                new_api = cls.create_api(cred1, cred2)
                cls.lock.release()
                return new_api
        return None

    @classmethod 
    def create_api(cls, cred1, cred2):
        """ Create an instance of the API depending on the credentials

        """
        key = cls._make_key(cred1,cred2)
        new_api = ClientAPI(cred1,cred2)
        cls._apis[key] = {}
        cls._apis[key]['api'] = new_api
        cls._apis[key]['cnt'] = 1
        return new_api

    @classmethod 
    def release_api(cls, cred1, cred2):
        """ Release the API with this credentials

        """
        if cred1 and cred2:
            key = cls._make_key(cred1,cred2)
            if key in cls._apis:
                cls._apis[key]['cnt'] -= 1
                if cls._apis[key]['cnt'] == 0:
                    new_api = cls._apis[key]['api']
                    # if necessary, we can disconnect
                    new_api.disconnect()


    @classmethod 
    def _make_key(cls, *args):
        """ Hash the credentials in order to create a key

        :param args: list of arguments used to create the hash (server, user, port, ...)
        :type args: list

        """
        skey = "".join(map(str, args))
        return hashlib.md5(skey).hexdigest()



