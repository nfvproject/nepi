#!/usr/bin/env python
# -*- coding: utf-8 -*-

class AttributesMap(object):
    """AttributesMap is the base class for every object whose attributes 
    are going to be manipulated by the end-user in a script or GUI.
    """
    def __init__(self):
        self._attributes = dict()

    @property
    def attributes(self):
        return self._attributes.values()

    @property
    def attributes_name(self):
        return self._attributes.keys()

    def set_attribute_value(self, name, value):
        self._attributes[name].value = value

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
        allowed = None, readonly = False, validation_function = None):
        if name in self._attributes:
            raise AttributeError("Attribute %s already exists" % name)
        attribute = Attribute(name, help, type, value, range, allowed, readonly,
                validation_function)
        self._attributes[name] = attribute

    def del_attribute(self, name):
        del self._attributes[name]

    def has_attribute(self, name):
        return name in self._attributes    
    
    def destroy(self):
        self._attributes = dict()

class Attribute(object):
    STRING, BOOL, ENUM, DOUBLE, INTEGER = (
		"STRING", "BOOL", "ENUM", "DOUBLE", "INTEGER")

    types = [STRING, BOOL, ENUM, DOUBLE, INTEGER]

    def __init__(self, name, help, type, value = None, range = None,
        allowed = None, readonly = False, validation_function = None):
        if not type in Attribute.types:
            raise AttributeError("invalid type %s " % type)
        self.name = name
        self._type = type
        self._help = help
        self._value = value
        self._validation_function = validation_function
        self._readonly = (readonly == True)
        self._modified = False
        # range: max and min possible values
        self._range = range
        # list of possible values
        self._allowed = allowed

    @property
    def type(self):
        return self._type

    @property
    def help(self):
        return self._help

    @property
    def readonly(self):
        return self._readonly

    @property
    def modified(self):
        return self._modified

    @property
    def range(self):
        return self._range

    @property
    def allowed(self):
        return self._allowed

    @property
    def validation_function(self):
        return self._validation_function

    def get_value(self):
        return self._value

    def set_value(self, value):
        if self._is_in_range(value) and \
                self._is_in_allowed_values(value) and \
                self._is_valid(value):
            self._value = value
            self._modified = True
        else:
            raise RuntimeError("Invalid value %s for attribute %s" %
                    (str(value), self.name))

    value = property(get_value, set_value)

    def _is_in_range(self, value):
        return not self.range or \
                (value >= self.range[0] and value <= self.range[1])

    def _is_in_allowed_values(self, value):
        return not self.allowed or value in self._allowed

    def _is_valid(self, value):
        return not self._validation_function or self._validation_function(value)

