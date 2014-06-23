import hashlib
import threading

from nepi.resources.iotlab.iotlab_api import IOTLABAPI

class IOTLABAPIFactory(object):
    """ 
    .. note::

        It allows the different RM to use the same REST client if they use 
        the same credentials.

    """
    # use lock to avoid concurrent access to the Api list at the same times by 2 
    # different threads
    lock = threading.Lock()
    _apis = dict()

    @classmethod 
    def get_api(cls, username, password, hostname, exp_id = None):
        """ Get an instance of the IoT-LAB REST API depending on the credentials
        """
        if username and password:
            key = cls._make_key(username, password, exp_id)
            cls.lock.acquire()
            if key in cls._apis:
                cls._apis[key]['cnt'] += 1
                cls.lock.release()
                return cls._apis[key]['api']
            else :
                iotlab_api = cls.create_api(username, password, hostname, exp_id)
                cls.lock.release()
                return iotlab_api
        return None

    @classmethod 
    def create_api(cls, username, password, hostname, exp_id = None):
        """ Create an instance of the IoT-LAB REST API depending on the credentials

        """
        key = cls._make_key(username, password, exp_id)
        iotlab_api = IOTLABAPI(username, password, hostname, exp_id)
        cls._apis[key] = {}
        cls._apis[key]['api'] = iotlab_api
        cls._apis[key]['cnt'] = 1
        return iotlab_api

    @classmethod 
    def release_api(cls, username, password, hostname, exp_id = None):
        """ Release the API with this credentials

        """
        if username and password:
            key = cls._make_key(username, password, exp_id)
            if key in cls._apis:
                cls._apis[key]['cnt'] -= 1
                if cls._apis[key]['cnt'] == 0:
                    iotlab_api = cls._apis[key]['api']
                    # if necessary, we can disconnect
                    iotlab_api.disconnect()


    @classmethod 
    def _make_key(cls, *args):
        """ Hash the credentials in order to create a key

        :param args: list of arguments used to create the hash (server, user, port, ...)
        :type args: list

        """
        skey = "".join(map(str, args))
        return hashlib.md5(skey).hexdigest()
