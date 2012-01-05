# -*- coding: utf-8 -*-

import ipaddr
import logging
import re

from nepi.design.tags import Taggable


class AttributeTypes(object):
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


class AttributeFlags(object):
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


class AttributeInfo(Taggable):
    """ The responsability of an AttributeInfo class is to provide attribute
    information but not attribute state """
    def __init__(self, name, help, type, clazz, args = None, 
            default_value = None, flags = None, tags = []):
        super(AttributeInfo, self).__init__()
        if not type in AttributeTypes.types:
            raise AttributeError("invalid type %s " % type)
        self._name = name
        self._type = type
        self._help = help
        # attribute construction class
        self._clazz = clazz
        self._args = args
        self._default_value = default_value
        self._flags = flags if flags != None else AttributeFlags.NoFlags
        for tag in tags:
            self.add_tag(tag)

    @property
    def name(self):
        return self._name

    @property
    def default_value(self):
        return self._default_value

    @property
    def type(self):
        return self._type

    @property
    def help(self):
        return self._help

    @property
    def clazz(self):
        return self._clazz

    @property
    def args(self):
        # Is it more optimal to store an empty dict in args
        # or to create one on demand that will soon be derreferenced?
        return dict() if not self._args else self._args

    @property
    def flags(self):
        return self._flags


class Attribute(object):
    """ The responsability of an Attribute class is to provide attribute
    value validation """
    def __init__(self, attr_info):
        super(Attribute, self).__init__()
        self._attr_info = attr_info
        self._value = attr_info.default_value
        self._modified = False
        self.container = None
      
        self._logger = logging.getLogger("nepi.design.attributes")

    @property
    def modified(self):
        return self._modified

    def get_value(self):
        return self._value

    def set_value(self, value):
        if self.is_valid(value):
            self._value = value
            self._modified = True
            return True
        return False

    value = property(get_value, set_value)

    def is_valid(self, value):
        raise NotImplementedError

    @property
    def name(self):
        return self._attr_info.name

    @property
    def type(self):
        return self._attr_info.type

    @property
    def help(self):
        return self._attr_info.help

    @property
    def default_value(self):
        return self._attr_info.default_value

    @property
    def tags(self):
        return self._attr_info.tags

    def has_flag(self, flag):
        return (self._attr_info.flags & flag) == flag

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


class EnumAttribute(Attribute):
    def __init__(self, attr_info):
        super(EnumAttribute, self).__init__(attr_info)
        if self.type != AttributeTypes.ENUM:
            raise AttributeError("invalid type %s for EnumAttribute" % 
                    self.type)
        self._allowed = self._attr_info.args.get("allowed", [])

    @property
    def allowed(self):
        return self._allowed

    def is_valid(self, value):
        if isinstance(value, str) and value in self.allowed:
            return True
        self._logger.error("Wrong value %r for EnumAttribute %s. Allowed are %s.", 
                str(value), self.name, self.allowed)
        return False


class BoolAttribute(Attribute):
    def __init__(self, attr_info):
        super(BoolAttribute, self).__init__(attr_info)
        if self.type != AttributeTypes.BOOL:
            raise AttributeError("invalid type %s for BoolAttribute" % 
                    self.type)

    def is_valid(self, value):
        if isinstance(value, bool):
            return True
        self._logger.error("Wrong value %r for BoolAttribute %s",
                str(value), self.name)
        return False


class RangeAttribute(Attribute):
    def __init__(self, attr_info):
        super(RangeAttribute, self).__init__(attr_info)
        self._min = self._attr_info.args.get("min")
        self._max = self._attr_info.args.get("max")

    @property
    def min(self):
        return self._min

    @property
    def max(self):
        return self._max

    def _is_in_range(self, value):
        return (not self.min or value >= self.min) and \
               (not self.max or value <= self.max)


class DoubleAttribute(RangeAttribute):
    def __init__(self, attr_info):
        super(DoubleAttribute, self).__init__(attr_info)
        if self.type != AttributeTypes.DOUBLE:
            raise AttributeError("invalid type %s for DoubleAttribute" % 
                    self.type)

    def is_valid(self, value):
        if self._is_in_range(value) and isinstance(value, float):
            return True
        self._logger.error("Wrong value %r for DoubleAttribute %s",
                str(value), self.name)
        return False


class IntegerAttribute(RangeAttribute):
    def __init__(self, attr_info):
        super(IntegerAttribute, self).__init__(attr_info)
        if self.type != AttributeTypes.INTEGER:
            raise AttributeError("invalid type %s for IntegerAttribute" % 
                    self.type)

    def is_valid(self, value):
        if self._is_in_range(value) and isinstance(value, int):
            return True
        self._logger.error("Wrong value %r for IntegerAttribute %s",
                str(value), self.name)
        return False

class NumberAttribute(RangeAttribute):
    def __init__(self, attr_info):
        super(NumberAttribute, self).__init__(attr_info)
        if self.type not in [AttributeTypes.INTEGER, AttributeTypes.DOUBLE]:
            raise AttributeError("invalid type %s for NumberAttribute" % 
                    self.type)

    def is_valid(self, value):
        if self._is_in_range(value) and isinstance(value, (float, int, long)):
            return True
        self._logger.error("Wrong value %r for NumberAttribute %s",
                str(value), self.name)
        return False


class StringAttribute(Attribute):
    def __init__(self, attr_info):
        super(StringAttribute, self).__init__(attr_info)
        if self.type != AttributeTypes.STRING:
            raise AttributeError("invalid type %s for StringAttribute" % 
                    self.type)

    def is_valid(self, value):
        if isinstance(value, str):
            return True
        self._logger.error("Wrong value %r for StringAttribute %s",
                str(value), self.name)
        return False


class TimeAttribute(Attribute):
    def __init__(self, attr_info):
        super(TimeAttribute, self).__init__(attr_info)
        if self.type != AttributeTypes.STRING:
            raise AttributeError("invalid type %s for TimeAttribute" % 
                    self.type)

    def is_valid(self, value):
        # TODO: Missing validation
        if isinstance(value, str):
            return True
        self._logger.error("Wrong value %r for TimeAttribute %s",
                str(value), self.name)
        return False


class IPv4Attribute(Attribute):
    def __init__(self, attr_info):
        super(IPv4Attribute, self).__init__(attr_info)
        if self.type != AttributeTypes.STRING:
            raise AttributeError("invalid type %s for IPv4Attribute" % 
                    self.type)

    def _is_valid_ipv4(self, value):
        try:
            ipaddr.IPv4Address(value)
        except ipaddr.AddressValueError:
            return False
        return True

    def is_valid(self, value):
        if not self._is_valid_ipv4(value):
            self._logger.error("Wrong value %r for IPV4Attribute %s",
                    str(value), self.name)
            return False
        return True


class IPv6Attribute(Attribute):
    def __init__(self, attr_info):
        super(IPv6Attribute, self).__init__(attr_info)
        if self.type != AttributeTypes.STRING:
            raise AttributeError("invalid type %s for IPv6Attribute" % 
                    self.type)

    def _is_valid_ipv6(self, value):
        try:
            ipaddr.IPv6Address(value)
        except ipaddr.AddressValueError:
            return False
        return True

    def is_valid(self, value):
        if not self._is_valid_ipv6(value):
            self._logger.error("Wrong value %r for IPv6Attribute %s",
                    str(value), self.name)
            return False
        return True


class IPAttribute(IPv4Attribute, IPv6Attribute):
    def __init__(self, attr_info):
        super(IPAttribute, self).__init__(attr_info)
        if self.type != AttributeTypes.STRING:
            raise AttributeError("invalid type %s for IPAttribute" % 
                    self.type)

    def is_valid(self, value):
        if not self._is_valid_ipv4(value) and \
            not self._is_valid_ipv6(value):
            self._logger.error("Wrong value %r for IPAttribute %s",
                    str(value), self.name)
            return False
        return True


class NetRefAttribute(IPAttribute):
    def __init__(self, attr_info):
        super(IPAttribute, self).__init__(attr_info)
        if self.type != AttributeTypes.STRING:
            raise AttributeError("invalid type %s for NetRefAttribute" % 
                    self.type)

    def is_valid(self, value):
        # TODO: Allow netrefs!
        if isinstance(value, str):
            return True
        self._logger.error("Wrong value %r for NetRefAttribute %s",
                str(value), self.name)
        return False


class MacAddressAttribute(Attribute):
    def __init__(self, attr_info):
        super(MacAddressAttribute, self).__init__(attr_info)
        if self.type != AttributeTypes.STRING:
            raise AttributeError("invalid type %s for MacAddressAttribute" % 
                    self.type)

    def is_valid(self, value):
        regex = r'^([0-9a-zA-Z]{0,2}:)*[0-9a-zA-Z]{0,2}'
        found = re.search(regex, value)
        if not found or value.count(':') != 5:
            return False
            self._logger.error("Wrong value %r for MacAddressAttribute %s",
                    str(value), self.name)
        return True

