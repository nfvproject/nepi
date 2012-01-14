# -*- coding: utf-8 -*-

from nepi.util.parser import sfa

class SFIAPI(object):
    def __init__(self):
        self._slice_tags = dict()
        self._slice_nodes = set()
        self._all_nodes = dict()
        self._slice_id = None

    def FetchSliceInfo(self, slice_id):
        self._slice_id = slice_id
        p = sfa.SFAResourcesParser()
        import commands
        xml = commands.getoutput("sfi.py resources")
        self._all_nodes = p.resources_from_xml(xml)
        xml = commands.getoutput("sfi.py resources %s" % slice_id)
        self._slice_tags, self._slice_nodes = p.slice_info_from_xml(xml)
    
    def GetSliceNodes(self, slicename):
        return list(self._slice_nodes)

    def GetNodeInfo(self, node_id):
        # TODO: thread-unsafe!! sanitize!
        info = self.GetNodes(node_id)
        tags = self.GetNodeTags(node_id=node_id, fields=('tagname','value'))
        return info, tags

    def GetSliceId(self, slicename):
        return self._slice_id

    def GetSliceVnetSysTag(self, slicename):
        return self._slice_tags.get('vsys_net')

    def GetNodeTags(self, node_id=None, fields=None, **kw):
        nodes = self._all_nodes
        if node_id is not None:
            node_ids = node_id
            if not isinstance(node_id, list):
                node_ids = [node_ids]
            nodes = self._FilterByNodeId(nodes, node_ids)
        else:
            filters = kw.pop('filters',{})
            if '|slice_ids' in filters:
                nodes = self._FilterByNodeId(nodes, self._slice_nodes)
                del filters['|slice_ids']
            nodes = self._FilterByFilters(nodes, filters)
        tagnames = kw.pop('tagname',[])
        return self._GetTagInfo(nodes, tagnames, fields)

    def GetNodes(self, nodeIdOrName=None, fields=[], **kw):
        #TODO: filter - peer
        nodes = self._all_nodes
        if nodeIdOrName is not None:
            node_ids = nodeIdOrName
            if not isinstance(nodeIdOrName, list):
                node_ids = [node_ids]
            nodes = self._FilterByNodeId(nodes, node_ids)
        else:
            filters = kw.pop('filters',{})
            if '|slice_ids' in filters:
                nodes = self._FilterByNodeId(nodes, self._slice_nodes)
                del filters['|slice_ids']
            # TODO: Remove this!! need to allow filter '>last_contact' !!!
            for f in ['>last_contact', 'node_type', 'run_level']:
                if f in filters:
                    del filters[f]
            nodes = self._FilterByFilters(nodes, filters)
        return self._GetNodeFieldsInfo(nodes, fields)
    
    def _FilterByNodeId(self, nodes, node_ids):
        return dict((k, nodes[k]) for k in node_ids if k in nodes)

    def _FilterByFilters(self, nodes, filters):
        def has_all_tags(node_id):
            data = nodes[node_id]
            for name, value in filters.iteritems():
                #if  (name == '>last_contact' and data['lastcontact'] > value) or \
                if (not name in data or data[name] != value):
                    return False
            return True
        return dict((k, value) for k, value in nodes.iteritems() if has_all_tags(k))

    def _GetNodeFieldsInfo(self, nodes, fields):
        result = list()
        for k, data in nodes.iteritems():
            if not fields:
                result.append(data)
                continue
            r_data = dict()
            for f in fields:
                if f == "node_id":
                    value = k
                else:
                    value = data[f]
                r_data[f] = value
            result.append(r_data)
        return result

    def _GetTagInfo(self, nodes, tagnames, fields):
        result = list()
        for k, data in nodes.iteritems():
            for name, value in data.iteritems():
                r_data = dict()
                if tagnames and name not in tagnames:
                    continue
                for f in fields:
                    if f == "node_id":
                        val = k
                    if f == "tagname":
                        val = name
                    if f == "value":
                        val = value
                    r_data[f] = val
                result.append(r_data)
        return result

    def AddSliceNodes(self, slicename, nodes=None):
        import os, commands, tempfile
        nodes = set(nodes)
        nodes.update(self._slice_nodes)
        nodes_data = dict((k, self._all_nodes[k]) for k in nodes)
        p = sfa.SFAResourcesParser()
        xml = p.create_slice_xml(nodes_data, self._slice_tags)
        fh, fname = tempfile.mkstemp()
        os.write(fh, xml)
        os.close(fh)
        out = commands.getoutput("sfi.py create %s %s" % (self._slice_id, fname))
        os.remove(fname)
        #print out

def sfiapi(slice_id):
    api = SFIAPI()
    api.FetchSliceInfo(slice_id)
    return api

