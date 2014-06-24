from nepi.util.logger import Logger
from requests.auth import HTTPBasicAuth
import requests
from urlparse import urljoin
from os.path import expanduser, basename
from cStringIO import StringIO
import json

class IOTLABAPI(Logger):
    """
       This class is the implementation of a REST IOt-LAB API. 

    """
    
    urlrest = 'https://www.iot-lab.info/rest/'  # url of the REST server

    def __init__(self, username=None, password=None, hostname=None, 
            exp_id = None):
        """
        :param username: Rest user login
        :type user: str
        :param password: Rest user password
        :type password: str
        """
        super(IOTLABAPI, self).__init__("IOTLABAPI")
        self.username = username # login of the user
        self.password = password # password of the user
        self.hostname = hostname # hostname of the node
        self.auth = HTTPBasicAuth(self.username, self.password)
        self.exp_id = self._get_experiment_id(exp_id)

    def _rest_method(self, url, method='GET', data=None):
        """
        :param url: url of API.
        :param method: request method
        :param data: request data
        """
        method_url = urljoin(IOTLABAPI.urlrest, url)
        if method == 'POST':
            headers = {'content-type': 'application/json'}
            req = requests.post(method_url, data=data, headers=headers,
                                auth=self._auth)
        elif method == 'MULTIPART':
            req = requests.post(method_url, files=data, auth=self.auth)
        elif method == 'DELETE':
            req = requests.delete(method_url, auth=self.auth)
        else:
            req = requests.get(method_url, auth=self.auth)

        if req.status_code == requests.codes.ok:
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
        if not 'exp-' in exp_id:
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
        msg = self._rest_method('experiments/%s/nodes?start' % self.exp_id,
                            method='POST', data='['+self.hostname+']')
        self.info(msg)

    def stop(self):
        """ Stop command on IoT-LAB node
        """
        msg = self._rest_method('experiments/%s/nodes?stop' % self.exp_id,
                           method='POST', data='['+self.hostname+']')
        self.info(msg)

    def reset(self):
        """ Reset command on IoT-LAB node
        """
        msg = self._rest_method('experiments/%s/nodes?reset' % self.exp_id,
                          method='POST', data='['+self.hostname+']')
        self.info(msg)

    def update(self, firmware_path):
        """ Update command (flash firmware) on IoT-LAB node
        """
        files = {}
        firmware_name, firmware_data = self._open_firmware(firmware_path)
        json_file = StringIO('['+self.hostname+']')
        files['firmware_name'] = firmware_data
        files['node.json'] = json_file.read()
        msg = self._rest_method('experiments/%s/nodes?update' % self.exp_id,
                          method='MULTIPART', data=files)
        self.info(msg)

    def disconnect(self) :
        """ Delete the session and logger topics. Then disconnect 

        """
        msg = " Disconnected IoT-LAB API"
        self.debug(msg)