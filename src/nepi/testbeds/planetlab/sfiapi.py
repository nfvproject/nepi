class SFIAPI(object):
    def __init__(self):
        self._slice_nodes = dict()
        self._all_nodes = dict()
    
    def GetSliceNodes(self, slicename):
        return None

    def AddSliceNodes(self, slicename, nodes=None):
        pass

    def GetNodeTags(self, nodeTagId=None, fields=None, **kw):
        pass

    def GetNodes(self, filters=basefilters, fields=('node_id','interface_ids')) ))

def sfiapi():
    return SFIAPI()

