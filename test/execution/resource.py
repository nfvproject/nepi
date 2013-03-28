#!/usr/bin/env python
from neco.execution.resource import ResourceManager, ResourceFactory, clsinit
from neco.execution.attribute import Attribute

import unittest

@clsinit
class MyResource(ResourceManager):
    _rtype = "MyResource"

    @classmethod
    def _register_attributes(cls):
        cool_attr = Attribute("my_attr", "is a really nice attribute!")
        cls._register_attribute(cool_attr)

    def __init__(self, ec, guid):
        super(MyResource, self).__init__(ec, guid)

@clsinit
class AnotherResource(ResourceManager):
    _rtype = "AnotherResource"

    def __init__(self, ec, guid):
        super(AnotherResource, self).__init__(ec, guid)
     
class EC(object):
    pass


class ResourceTestCase(unittest.TestCase):
    def test_add_resource_factory(self):
        ResourceFactory.register_type(MyResource)
        ResourceFactory.register_type(AnotherResource)

        self.assertEquals(MyResource.rtype(), "MyResource")
        self.assertEquals(len(MyResource._attributes), 1)

        self.assertEquals(Resource.rtype(), "Resource")
        self.assertEquals(len(Resource._attributes), 0)

        self.assertEquals(AnotherResource.rtype(), "AnotherResource")
        self.assertEquals(len(AnotherResource._attributes), 0)

        #self.assertEquals(OmfNode.rtype(), "OmfNode")
        #self.assertEquals(len(OmfNode._attributes), 0)

        self.assertEquals(len(ResourceFactory.resource_types()), 2)

if __name__ == '__main__':
    unittest.main()

