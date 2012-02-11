
import copy
import ipaddr
import logging
import re
import weakref

from nepi.design.tags import Taggable

def is_valid_ipv6(value):
    try:
        ipaddr.IPv6Address(value)
    except ipaddr.AddressValueError:
        return False
    return True

def is_valid_ipv4(value):
    try:
        ipaddr.IPv4Address(value)
    except ipaddr.AddressValueError:
        return False
    return True


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


    flags_t = dict({
        "NoFlags": NoFlags,
        "DesignReadOnly": DesignReadOnly,
        "DesignInvisible": DesignInvisible,
        "ExecReadOnly": ExecReadOnly,
        "ExecInvisible": ExecInvisible,
        "ExecImmutable": ExecImmutable,
        "NoDefaultValue": NoDefaultValue,
        "Metadata": Metadata,
        })


class AttributesMapProxy(object):
    def __init__(self, owner):
        self._owner = weakref.ref(owner)
    
    def __getattr__(self, name):
        return self._owner()._attributes[name]

    def __setattr__(self, name, value):
        if name != "_owner":
            raise RuntimeError("Can't override attribute")
        super(AttributesMapProxy, self).__setattr__(name, value)


class AttributesMap(object):
    def __init__(self):
        super(AttributesMap, self).__init__()
        self._attributes = dict()
        self._a = AttributesMapProxy(self)

    @property
    def attributes(self):
        return self._attributes.keys()

    @property
    def a(self):
        return self._a

    def add_attr(self, attr):
        self._attributes[attr.name] = attr
        attr.owner = self

    def clone_attrs(self, other):
        self._a = AttributesMapProxy(self)
        self._attributes = dict()
        for attr in other._attributes.values():
            new = attr.clone()
            self.add_attr(new)


class FlagProxy(object):
    def __init__(self, owner):
        self._owner = weakref.ref(owner)
    
    def __getattr__(self, name):
        return self._owner().has_flag(getattr(AttributeFlags, name))

    def __setattr__(self, name, value):
        if name != "_owner":
            raise RuntimeError("Can't override attribute")
        super(FlagProxy, self).__setattr__(name, value)


class Attribute(Taggable):
    """ The responsability of an Attribute class is to provide attribute
    value validation """
    def __init__(self, name, help, type, default_value = None, 
            flags = None, tags = []):
        super(Attribute, self).__init__()
        if not type in AttributeTypes.types:
            raise AttributeError("invalid type %s " % type)
        self._name = name
        self._type = type
        self._help = help
        self._default_value = default_value
        self._flags = flags if flags != None else AttributeFlags.NoFlags
        self._flag_proxy = FlagProxy(self)
        self._value = default_value
        self._modified = False
        self._owner = None
        
        for tag in tags:
            self.add_tag(tag)
    
        self._logger = logging.getLogger("nepi.design.attributes")

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
    def f(self):
        return self._flag_proxy

    @property
    def flags(self):
        return [fn for fn in AttributeFlags.flags_t.keys() if getattr(self.f, fn)]

    @property
    def modified(self):
        return self._modified

    def get_owner(self):
        # Gives back a strong-reference not a weak one
        return self._owner()

    def set_owner(self, owner):
        self._owner = weakref.ref(owner)

    owner = property(get_owner, set_owner)

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

    def has_flag(self, flag):
        return (self._flags & flag) == flag

    def clone(self):
        new = copy.copy(self)
        # need to make a new FlagProxy
        new._flag_proxy = FlagProxy(new)
        return new


class EnumAttribute(Attribute):
    def __init__(self, name, help, default_value = None, 
            flags = None, tags = [], allowed = []):
        type = AttributeTypes.ENUM
        super(EnumAttribute, self).__init__(name, help, type, 
                default_value, flags, tags)
        self._allowed = allowed

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
    def __init__(self, name, help, default_value = None, 
            flags = None, tags = []):
        type = AttributeTypes.BOOL
        super(BoolAttribute, self).__init__(name, help, type, 
                default_value, flags, tags)

    def is_valid(self, value):
        if isinstance(value, bool):
            return True
        self._logger.error("Wrong value %r for BoolAttribute %s",
                str(value), self.name)
        return False


class RangeAttribute(Attribute):
    def __init__(self, name, help, type, default_value = None, 
            flags = None, tags = [], min = None, max = None):
        super(RangeAttribute, self).__init__(name, help, type, 
                default_value, flags, tags)
        self._min = min
        self._max = max

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
    def __init__(self, name, help, default_value = None, 
            flags = None, tags = [], min = None, max = None):
        type = AttributeTypes.DOUBLE
        super(DoubleAttribute, self).__init__(name, help, type, 
                default_value, flags, tags, min, max)

    def is_valid(self, value):
        if self._is_in_range(value) and isinstance(value, float):
            return True
        self._logger.error("Wrong value %r for DoubleAttribute %s",
                str(value), self.name)
        return False


class IntegerAttribute(RangeAttribute):
    def __init__(self, name, help, default_value = None, 
            flags = None, tags = [], min = None, max = None):
        type = AttributeTypes.INTEGER
        super(IntegerAttribute, self).__init__(name, help, type, 
                default_value, flags, tags, min, max)

    def is_valid(self, value):
        if self._is_in_range(value) and isinstance(value, int):
            return True
        self._logger.error("Wrong value %r for IntegerAttribute %s",
                str(value), self.name)
        return False


class NumberAttribute(RangeAttribute):
    def __init__(self, name, help, type, default_value = None, 
            flags = None, tags = [], min = None, max = None):
        if self.type not in [AttributeTypes.INTEGER, AttributeTypes.DOUBLE]:
            raise AttributeError("invalid type %s for NumberAttribute" % 
                    self.type)
        super(NumberAttribute, self).__init__(name, help, type, 
                default_value, flags, tags, min, max)

    def is_valid(self, value):
        if self._is_in_range(value) and isinstance(value, (float, int, long)):
            return True
        self._logger.error("Wrong value %r for NumberAttribute %s",
                str(value), self.name)
        return False


class StringAttribute(Attribute):
    def __init__(self, name, help, default_value = None, 
            flags = None, tags = []):
        type = AttributeTypes.STRING
        super(StringAttribute, self).__init__(name, help, type, 
                default_value, flags, tags)

    def is_valid(self, value):
        if isinstance(value, str):
            return True
        self._logger.error("Wrong value %r for StringAttribute %s",
                str(value), self.name)
        return False


class TimeAttribute(Attribute):
    def __init__(self, name, help, default_value = None, 
            flags = None, tags = []):
        type = AttributeTypes.STRING
        super(TimeAttribute, self).__init__(name, help, type, 
                default_value, flags, tags)

    def is_valid(self, value):
        # TODO: Missing validation
        if isinstance(value, str):
            return True
        self._logger.error("Wrong value %r for TimeAttribute %s",
                str(value), self.name)
        return False


class IPv4Attribute(Attribute):
    def __init__(self, name, help, default_value = None, 
            flags = None, tags = []):
        type = AttributeTypes.STRING
        super(IPv4Attribute, self).__init__(name, help, type, 
                default_value, flags, tags)

    def is_valid(self, value):
        if not is_valid_ipv4(value):
            self._logger.error("Wrong value %r for IPV4Attribute %s",
                    str(value), self.name)
            return False
        return True


class IPv6Attribute(Attribute):
    def __init__(self, name, help, default_value = None, 
            flags = None, tags = []):
        type = AttributeTypes.STRING
        super(IPv6Attribute, self).__init__(name, help, type, 
                default_value, flags, tags)

    def is_valid(self, value):
        if not is_valid_ipv6(value):
            self._logger.error("Wrong value %r for IPv6Attribute %s",
                    str(value), self.name)
            return False
        return True


class IPAttribute(Attribute):
    def __init__(self, name, help, default_value = None, 
            flags = None, tags = []):
        type = AttributeTypes.STRING
        super(IPAttribute, self).__init__(name, help, type, 
                default_value, flags, tags)

    def is_valid(self, value):
        if not is_valid_ipv4(value) and \
            not is_valid_ipv6(value):
            self._logger.error("Wrong value %r for IPAttribute %s",
                    str(value), self.name)
            return False
        return True


class NetRefAttribute(IPAttribute):
    def __init__(self, name, help, default_value = None, 
            flags = None, tags = []):
        type = AttributeTypes.STRING
        super(NetRefAttribute, self).__init__(name, help,  
                default_value, flags, tags)

    def is_valid(self, value):
        # TODO: Allow netrefs!
        if isinstance(value, str):
            return True
        self._logger.error("Wrong value %r for NetRefAttribute %s",
                str(value), self.name)
        return False


class MacAddressAttribute(Attribute):
    def __init__(self, name, help, default_value = None, 
            flags = None, tags = []):
        type = AttributeTypes.STRING
        super(MacAddressAttribute, self).__init__(name, help, type, 
                default_value, flags, tags)

    def is_valid(self, value):
        regex = r'^([0-9a-zA-Z]{0,2}:)*[0-9a-zA-Z]{0,2}'
        found = re.search(regex, value)
        if not found or value.count(':') != 5:
            return False
            self._logger.error("Wrong value %r for MacAddressAttribute %s",
                    str(value), self.name)
        return True


