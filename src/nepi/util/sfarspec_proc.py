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

from nepi.util.logger import Logger
try:
    from sfa.rspecs.rspec import RSpec
    from sfa.util.xrn import Xrn, get_leaf, get_authority, hrn_to_urn, urn_to_hrn
except ImportError:
    log = Logger("SFA RSpec Processing")
    log.debug("Package sfa-common not installed.\
         Could not import sfa.rspecs.rspec and sfa.util.xrn")

from types import StringTypes, ListType


class SfaRSpecProcessing(object):
    """
    Class to process SFA RSpecs, parse the RSpec replies such as Advertisement RSpecs,
    and build in the case of Request RSpecs.
    """
    def __init__(self, config=None):
        self._log = Logger("SFA RSpec Processing")
        self.config = config 

    def make_dict_rec(self, obj):
        if not obj or isinstance(obj, (StringTypes, bool)):
            return obj
        if isinstance(obj, list):
            objcopy = []
            for x in obj:
                objcopy.append(self.make_dict_rec(x))
            return objcopy
        # We thus suppose we have a child of dict
        objcopy = {}
        for k, v in obj.items():
            objcopy[k] = self.make_dict_rec(v)
        return objcopy

    def parse_sfa_rspec(self, rspec_string):
        """
        Parse the RSpec XML as a string.
        """
        # rspec_type and rspec_version should be set in the config of the platform,
        # we use GENIv3 as default one if not
        if self.config:
            if 'rspec_type' and 'rspec_version' in self.config:
                rspec_version = self.config['rspec_type'] + ' ' + self.config['rspec_version']
        else:
            rspec_version = 'GENI 3'
        self._log.debug(rspec_version)
        rspec = RSpec(rspec_string, version=rspec_version)
        
        try:
            nodes = rspec.version.get_nodes()
        except Exception, e:
            self._log.warn("Could not retrieve nodes in RSpec: %s" % e)
        try:
            leases = rspec.version.get_leases()
        except Exception, e:
            self._log.warn("Could not retrieve leases in RSpec: %s" % e)
        try:
            links = rspec.version.get_links()
        except Exception, e:
            self._log.warn("Could not retrieve links in RSpec: %s" % e)
        try:
            channels = rspec.version.get_channels()
        except Exception, e:
            self._log.warn("Could not retrieve channels in RSpec: %s" % e)
  
        resources = [] 
        # Extend object and Format object field's name
        for node in nodes:
            node['type'] = 'node'
            node['network_hrn'] = Xrn(node['component_id']).authority[0] # network ? XXX
            node['hrn'] = urn_to_hrn(node['component_id'])[0]
            node['urn'] = node['component_id']
            node['hostname'] = node['component_name']
            node['initscripts'] = node.pop('pl_initscripts')
            if 'exclusive' in node and node['exclusive']:
                node['exclusive'] = node['exclusive'].lower() == 'true'
 
            # XXX This should use a MAP as before
            if 'position' in node: # iotlab
                node['x'] = node['position']['posx']
                node['y'] = node['position']['posy']
                node['z'] = node['position']['posz']
                del node['position']
 
            if 'location' in node:
                if node['location']:
                    node['latitude'] = node['location']['latitude']
                    node['longitude'] = node['location']['longitude']
                del node['location']
 
            # Flatten tags
            if 'tags' in node:
                if node['tags']:
                    for tag in node['tags']:
                        node[tag['tagname']] = tag['value']
                del node['tags']
 
            
            # We suppose we have children of dict that cannot be serialized
            # with xmlrpc, let's make dict
            resources.append(self.make_dict_rec(node))
 
        # NOTE a channel is a resource and should not be treated independently
        #     resource
        #        |
        #   +----+------+-------+
        #   |    |      |       |
        # node  link  channel  etc.
        #resources.extend(nodes)
        #resources.extend(channels)
 
        return {'resource': resources, 'lease': leases } 
#               'channel': channels \
#               }

 
    def build_sfa_rspec(self, slice_id, resources, leases):
        """
        Build the XML RSpec from list of resources' urns.
        eg. resources = ["urn:publicid:IDN+ple:modenaple+node+planetlab-1.ing.unimo.it"]
        """
        #if isinstance(resources, str):
        #    resources = eval(resources)
        # rspec_type and rspec_version should be set in the config of the platform,
        # we use GENIv3 as default one if not
        if self.config:
            if 'rspec_type' and 'rspec_version' in self.config:
                rspec_version = self.config['rspec_type'] + ' ' + self.config['rspec_version']
        else:
            rspec_version = 'GENI 3'

        # extend rspec version with "content_type"
        rspec_version += ' request'
        
        rspec = RSpec(version=rspec_version)

        nodes = []
        channels = []
        links = []
        self._log.info("Building RSpec for resources %s" % resources)
        for urn in resources:
            # XXX TO BE CORRECTED, this handles None values
            if not urn:
                continue
            self._log.info(urn)
            resource = dict()
            # TODO: take into account the case where we send a dict of URNs without keys
            #resource['component_id'] = resource.pop('urn')
            resource['component_id'] = urn
            resource_hrn, resource_type = urn_to_hrn(resource['component_id'])
            # build component_manager_id
            top_auth = resource_hrn.split('.')[0]
            cm = urn.split("+")
            resource['component_manager_id'] = "%s+%s+authority+cm" % (cm[0],top_auth)

            if resource_type == 'node':
                # XXX dirty hack WiLab !!!
                if self.config:
                    if 'wilab2' in self.config['sm']:
                        resource['client_id'] = "PC"
                        resource['sliver_type'] = "raw-pc"
                nodes.append(resource)
            elif resource_type == 'link':
                links.append(resource)
            elif resource_type == 'channel':
                channels.append(resource)
            else:
                raise Exception, "Not supported type of resource" 
        
        rspec.version.add_nodes(nodes, rspec_content_type="request")
        #rspec.version.add_leases(leases)
        #rspec.version.add_links(links)
        #rspec.version.add_channels(channels)
   
        self._log.info("request rspec: %s"%rspec.toxml())
        return rspec.toxml()


