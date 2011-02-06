# -*- coding: utf-8 -*-
# vim:ts=4:sw=4:et:ai:sts=4

class AttributesMap(object):
    """AttributesMap is the base class for every object whose attributes 
    are going to be manipulated by the end-user in a script or GUI.
    """
    def __init__(self):
        self._attributes = dict()

    @property
    def attributes_name(self):
        return set(self._attributes.keys())

    def is_valid_attribute_value(self, name, value):
        raise NotImplementedError

    def set_attribute_value(self, name, value):
        if self.is_valid_attribute_value(name, value):
            self._attributes[name].value = value
            return True
        return False

    def set_attribute_readonly(self, name, value):
        self._attributes[name].readonly = value

    def get_attribute_value(self, name):
        return self._attributes[name].value

    def get_attribute_help(self, name):
        return self._attributes[name].help

    def get_attribute_type(self, name):
        return self._attributes[name].type

    def get_attribute_range(self, name):
        return self._attributes[name].range

    def get_attribute_allowed(self, name):
        return self._attributes[name].allowed

    def get_attribute_readonly(self, name):
        return self._attributes[name].readonly

    def add_attribute(self, name, help, type, value = None, range = None,
        allowed = None, readonly = False):
        if name in self._attributes:
            raise AttributeError('Attribute %s already exists' % name))
        attribute = Attribute(name, help, type, value, range, allowed, readonly)
        self._attributes[name] = attribute

    def del_attribute(self, name):
        del self._attributes[name]

    def has_attribute(self, name):
        return name in self._attributes    
    
    def destroy(self):
        self._attributes = dict()

class Attribute(object):
    STRING , BOOL, ENUM, DOUBLE, INTEGER, ENDPOINT, TIME = (
		"STRING", "BOOL", "ENUM", "DOUBLE", "INTEGER", "ENDPOINT", "TIME")

    types = [STRING, BOOL, ENUM, DOUBLE, INTEGER, ENDPOINT, TIME]

    def __init__(self, name, help, type, value = None, range = None,
        allowed = None, readonly = False):
        if not type in Attribute.types:
            raise AttributeError("invalid type %s " % type)
        self.name = name
        self.value = value
        self.type = type
        self.help = help
        self.readonly = (readonly == True)
        self.modified = False
        # range: max and min possible values
        self.range = range
        # list of possible values
        self.allowed = allowed

