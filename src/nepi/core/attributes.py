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
    
    type_parsers = {
        STRING : str,
        BOOL : lambda x : str(x).lower() in ("1","on","yes","true"),
        ENUM : str,
        DOUBLE : float,
        INTEGER : int,
    }

    ### Attribute Flags
    NoFlags          = 0x00
    # Read-only attribute at design time
    DesignReadOnly   = 0x01
    # Invisible attribute at design time
    DesignInvisible  = 0x02
    # Read-only attribute at execution time
    ExecReadOnly     = 0x04
    # Invisible attribute at execution time
    ExecInvisible    = 0x08
    # Attribute doesn't change value during execution time
    ExecImmutable    = 0x10
    # Attribute has no default value in the testbed
    NoDefaultValue   = 0x20
    # Metadata attribute (is not directly reflected by a real object attribute)
    Metadata         = 0x40

    def __init__(self, name, help, type, value = None, range = None,
        allowed = None, flags = None, validation_function = None, 
        category = None):
        if not type in Attribute.types:
            raise AttributeError("invalid type %s " % type)
        self._name = name
        self._type = type
        self._help = help
        self._value = value
        self._flags = flags if flags != None else Attribute.NoFlags
        # range: max and min possible values
        self._range = range
        # list of possible values
        self._allowed = allowed
        self._validation_function = validation_function
        self._modified = False
        self._category = category

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
    def is_design_invisible(self):
        return self.has_flag(Attribute.DesignInvisible)

    @property
    def is_design_read_only(self):
        return self.has_flag(Attribute.DesignReadOnly)

    @property
    def is_exec_invisible(self):
        return self.has_flag(Attribute.ExecInvisible)

    @property
    def is_exec_read_only(self):
        return self.has_flag(Attribute.ExecReadOnly)

    @property
    def is_exec_immutable(self):
        return self.has_flag(Attribute.ExecImmutable)

    @property
    def is_metadata(self):
        return self.has_flag(Attribute.Metadata)

    @property
    def has_no_default_value(self):
        return self.has_flag(Attribute.NoDefaultValue)

    @property
    def modified(self):
        return self._modified

    @property
    def category(self):
        return self._category

    @property
    def range(self):
        return self._range

    @property
    def allowed(self):
        return self._allowed

    @property
    def validation_function(self):
        return self._validation_function

    def has_flag(self, flag):
        return (self._flags & flag) == flag

    def get_value(self):
        return self._value

    def set_value(self, value):
        if self.is_valid_value(value):
            self._value = value
            self._modified = True
        else:
            raise ValueError("Invalid value %s for attribute %s" %
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
        super(AttributesMap, self).__init__()
        self._attributes = dict()

    @property
    def attributes(self):
        return self._attributes.values()

    def get_attribute_list(self, filter_flags = None):
        attributes = self._attributes
        if filter_flags != None:
            def filter_attrs(attr_data):
                (attr_id, attr) = attr_data
                return attr.has_flag(filter_flags)
            attributes = dict(filter(filter_attrs, attributes.iteritems()))
        return attributes.keys()

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

    def get_attribute_category(self, name):
        return self._attributes[name].category

    def is_attribute_design_invisible(self, name):
        return self._attributes[name].is_design_invisible

    def is_attribute_design_read_only(self, name):
        return self._attributes[name].is_design_read_only

    def is_attribute_exec_invisible(self, name):
        return self._attributes[name].is_exec_invisible

    def is_attribute_exec_read_only(self, name):
        return self._attributes[name].is_exec_read_only

    def is_attribute_exec_immutable(self, name):
        return self._attributes[name].is_exec_immutable

    def is_attribute_metadata(self, name):
        return self._attributes[name].is_metadata

    def has_attribute_no_default_value(self, name):
        return self._attributes[name].has_no_default_value

    def is_attribute_modified(self, name):
        return self._attributes[name].modified

    def is_attribute_value_valid(self, name, value):
        return self._attributes[name].is_valid_value(value)

    def add_attribute(self, name, help, type, value = None, range = None,
        allowed = None, flags = Attribute.NoFlags, validation_function = None,
        category = None):
        if name in self._attributes:
            raise AttributeError("Attribute %s already exists" % name)
        attribute = Attribute(name, help, type, value, range, allowed, flags,
                validation_function, category)
        self._attributes[name] = attribute

    def del_attribute(self, name):
        del self._attributes[name]

    def has_attribute(self, name):
        return name in self._attributes    
    
    def destroy(self):
        self._attributes = dict()

