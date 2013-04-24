
### Attribute Types
class Types:
    String  = "STRING"
    Bool    = "BOOL"
    Enum    = "ENUM"
    Double  = "DOUBLE"
    Integer = "INTEGER"

### Attribute Flags
class Flags:
    # Attribute can be modified by the user 
    NoFlags         = 0x00
    # Attribute is not modifiable by the user
    ReadOnly        = 0x01
    # Attribute is an access credential
    Credential      = 0x02

class Attribute(object):
    def __init__(self, name, help, type = Types.String,
            flags = Flags.NoFlags, default = None):
        self._name = name
        self._help = help
        self._type = type
        self._flags = flags
        self._default = self._value = default

    @property
    def name(self):
        return self._name

    @property
    def default(self):
        return self._default

    @property
    def type(self):
        return self._type

    @property
    def help(self):
        return self._help

    @property
    def flags(self):
        return self._flags

    def has_flag(self, flag):
        return (self._flags & flag) == flag

    def get_value(self):
        return self._value

    def set_value(self, value):
        if self.is_valid_value(value):
            self._value = value
        else:
            raise ValueError("Invalid value %s for attribute %s" %
                    (str(value), self.name))

    value = property(get_value, set_value)

    def is_valid_value(self, value):
        """ Attribute subclasses will override this method to add 
        adequate validation"""
        return True

