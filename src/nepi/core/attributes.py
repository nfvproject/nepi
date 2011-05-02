#!/usr/bin/env python
# -*- coding: utf-8 -*-

class Attribute(object):
    ### Attribute types
    STRING  = "STRING"
    BOOL    = "BOOL"
    ENUM    = "ENUM"
    DOUBLE  = "DOUBLE"
    INTEGER = "INTEGER"

    types = [
        STRING, 
        BOOL, 
        ENUM, 
        DOUBLE, 
        INTEGER
    ]

    ### Attribute Flags
    NoFlags     = 0x00
    # Attribute is only modifiable during experiment design
    DesignOnly  = 0x01
    # Attribute is read only and can't be modified by the user
    # Note: ReadOnly implies DesignOnly
    ReadOnly    = 0x03
    # Attribute is invisible to the user but can be modified
    Invisible   = 0x04
    # Attribute has no default value in the testbed instance. 
    # So it needs to be set explicitely
    HasNoDefaultValue = 0x08

    def __init__(self, name, help, type, value = None, range = None,
        allowed = None, flags = NoFlags, validation_function = None):
        if not type in Attribute.types:
            raise AttributeError("invalid type %s " % type)
        self._name = name
        self._type = type
        self._help = help
        self._value = value
        self._flags = flags
        # range: max and min possible values
        self._range = range
        # list of possible values
        self._allowed = allowed
        self._validation_function = validation_function
        self._modified = False

    @property
    def name(self):
        return self._name

    @property
    def type(self):
        return self._type

    @property
    def help(self):
        return self._help

    @property
    def flags(self):
        return self._flags

    @property
    def invisible(self):
        return (self._flags & Attribute.Invisible) == Attribute.Invisible

    @property
    def read_only(self):
        return (self._flags & Attribute.ReadOnly) == Attribute.ReadOnly

    @property
    def has_no_default_value(self):
        return (self._flags & Attribute.HasNoDefaultValue) == \
                Attribute.HasNoDefaultValue

    @property
    def design_only(self):
        return (self._flags & Attribute.DesignOnly) == Attribute.DesignOnly

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
        if self.is_valid_value(value):
            self._value = value
            self._modified = True
        else:
            raise RuntimeError("Invalid value %s for attribute %s" %
                    (str(value), self.name))

    value = property(get_value, set_value)

    def is_valid_value(self, value):
        return self._is_in_range(value) and \
            self._is_in_allowed_values(value) and \
                self._is_valid(value)    

    def _is_in_range(self, value):
        return not self.range or \
                (value >= self.range[0] and value <= self.range[1])

    def _is_in_allowed_values(self, value):
        return not self._allowed or value in self._allowed

    def _is_valid(self, value):
        return not self._validation_function or \
                self._validation_function(self, value)

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
    def attributes_list(self):
        return self._attributes.keys()

    def set_attribute_value(self, name, value):
        self._attributes[name].value = value

    def get_attribute_value(self, name):
        return self._attributes[name].value

    def get_attribute_help(self, name):
        return self._attributes[name].help

    def get_attribute_type(self, name):
        return self._attributes[name].type

    def get_attribute_range(self, name):
        if not self._attributes[name].range:
            return (None, None)
        return self._attributes[name].range

    def get_attribute_allowed(self, name):
        return self._attributes[name].allowed

    def is_attribute_read_only(self, name):
        return self._attributes[name].read_only

    def is_attribute_invisible(self, name):
        return self._attributes[name].invisible

    def is_attribute_design_only(self, name):
        return self._attributes[name].design_only

    def has_attribute_no_default_value(self, name):
        return self._attributes[name].has_no_default_value

    def is_attribute_modified(self, name):
        return self._attributes[name].modified

    def is_attribute_value_valid(self, name, value):
        return self._attributes[name].is_valid_value(value)

    def add_attribute(self, name, help, type, value = None, range = None,
        allowed = None, flags = Attribute.NoFlags, validation_function = None):
        if name in self._attributes:
            raise AttributeError("Attribute %s already exists" % name)
        attribute = Attribute(name, help, type, value, range, allowed, flags,
                validation_function)
        self._attributes[name] = attribute

    def del_attribute(self, name):
        del self._attributes[name]

    def has_attribute(self, name):
        return name in self._attributes    
    
    def destroy(self):
        self._attributes = dict()

