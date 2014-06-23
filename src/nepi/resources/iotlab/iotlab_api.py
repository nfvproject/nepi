from nepi.util.logger import Logger
from requests.auth import HTTPBasicAuth
from requests.codes import ok
from requests import post, delete, get
from urlparse import urljoin
from os.path import expanduser, basename
from cStringIO import StringIO
import json

class IOTLABAPI(Logger):
    """
       This class is the implementation of a REST IOt-LAB API. 

    """
    def __init__(self, username=None, password=None, hostname=None, 
            exp_id = None):
        """
        :param username: Rest user login
        :type user: str
        :param password: Rest user password
        :type password: str
        """
        super(IOTLABAPI, self).__init__("IOTLABAPI")
        self._exp_id = self._get_experiment_id(exp_id)
        self._username = username # login of the user
        self._password = password # password of the user
        self._hostname = hostname # hostname of the node
        self._auth = HTTPBasicAuth(self._username, self._password)
        self._server = "https://www.iot-lab.info/rest/" # name of the REST server

    def _rest_method(self, url, method='GET', data=None):
        """
        :param url: url of API.
        :param method: request method
        :param data: request data
        """
        method_url = urljoin(self.url, url)
        if method == 'POST':
            headers = {'content-type': 'application/json'}
            req = post(method_url, data=data, headers=headers,
                                auth=self._auth)
        elif method == 'MULTIPART':
            req = post(method_url, files=data, auth=self._auth)
        elif method == 'DELETE':
            req = delete(method_url, auth=self._auth)
        else:
            req = get(method_url, auth=self._auth)

        if req.status_code == ok:
            return req.text
        # we have HTTP error (code != 200)
        else:
            msg = "HTTP error code : %d %s." % (req.status_code, req.text)
            self.error(msg)
            raise RuntimeError(msg)
    
    def _open_firmware(self, firmware_path):
        """ Open a firmware file 
        """
        try:
            # expanduser replace '~' with the correct path
            firmware_file = open(expanduser(firmware_path), 'r')
        except IOError as msg:
            self.error(msg)
            raise RuntimeError(msg)
        else:
            firmware_name = basename(firmware_file.name)
            firmware_data = firmware_file.read()
            firmware_file.close()
        return firmware_name, firmware_data
    
    def _get_experiments(self):
        """ Get user experiments list
        """
        queryset = "state=Running&limit=0&offset=0"
        return self._rest_method('experiments?%s' % queryset)

    def _get_experiment_id(self, exp_id = None):
        """ Get experiment id. 
        """
        if exp_id is not None:
            return exp_id
        else:
            exp_json = json.loads(self._get_experiments())
            items = exp_json["items"]
            if len(items) == 0:
                msg = "You don't have an experiment with state Running."
                self.error(msg)
                raise RuntimeError(msg)
            exps_id = [exp["id"] for exp in items]
            if len(exps_id) > 1:
                msg = "You have several experiments with state Running."
                self.error(msg)
                raise RuntimeError(msg)
            else:
                return exps_id[0]


    def start(self):
        """ Start command on IoT-LAB node
        """
        msg = self._rest_method('experiments/%s/nodes?start' % self._exp_id,
                            method='POST', data='['+self._hostname+']')
        self.info(msg)

    def stop(self):
        """ Stop command on IoT-LAB node
        """
        msg = self._rest_method('experiments/%s/nodes?stop' % self._exp_id,
                           method='POST', data='['+self._hostname+']')
        self.info(msg)

    def reset(self):
        """ Reset command on IoT-LAB node
        """
        msg = self._rest_method('experiments/%s/nodes?reset' % self._exp_id,
                          method='POST', data='['+self._hostname+']')
        self.info(msg)

    def update(self, firmware_path):
        """ Update command (flash firmware) on IoT-LAB node
        """
        files = {}
        firmware_name, firmware_data = self._open_firmware(firmware_path)
        json_file = StringIO('['+self._hostname+']')
        files['firmware_name'] = firmware_data
        files['node.json'] = json_file.read()
        msg = self._rest_method('experiments/%s/nodes?update' % self._exp_id,
                          method='MULTIPART', data=files)
        self.info(msg)
