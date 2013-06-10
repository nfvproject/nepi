#
#    NEPI, a framework to manage network experiments
#    Copyright (C) 2013 INRIA
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Author: Alina Quereilhac <alina.quereilhac@inria.fr>

### Attribute Types
class Types:
    String  = "STRING"
    Bool    = "BOOL"
    Enumerate    = "ENUM"
    Double  = "DOUBLE"
    Integer = "INTEGER"

### Attribute Flags
class Flags:
    """ Differents flags to characterize an attribute

    """
    # Attribute can be modified by the user 
    NoFlags         = 0x00
    # Attribute is not modifiable by the user
    ReadOnly        = 0x01
    # Attribute is not modifiable by the user during runtime
    ExecReadOnly        = 0x02
    # Attribute is an access credential
    Credential      = 0x04
    # Attribute is a filter used to discover resources
    Filter      = 0x08

class Attribute(object):
    """
    .. class:: Class Args :
      
        :param name: Name of the attribute
        :type name: str
        :param help: Help about the attribute
        :type help: str
        :param type: type of the attribute
        :type type: str
        :param flags: Help about the attribute
        :type flags: str
        :param default: Default value of the attribute
        :type default: str
        :param allowed: Allowed value for this attribute
        :type allowed: str
        :param range: Range of the attribute
        :type range: str
        :param set_hook: hook that is related with this attribute
        :type set_hook: str

    """
    def __init__(self, name, help, type = Types.String,
            flags = Flags.NoFlags, default = None, allowed = None,
            range = None, set_hook = None):
        self._name = name
        self._help = help
        self._type = type
        self._flags = flags
        self._allowed = allowed
        self._range = range
        self._default = self._value = default
        # callback to be invoked upon changing the 
        # attribute value
        self.set_hook = set_hook

    @property
    def name(self):
    """ Returns the name of the attribute """
        return self._name

    @property
    def default(self):
    """ Returns the default value of the attribute """
        return self._default

    @property
    def type(self):
    """ Returns the type of the attribute """
        return self._type

    @property
    def help(self):
    """ Returns the help of the attribute """
        return self._help

    @property
    def flags(self):
    """ Returns the flags of the attribute """
        return self._flags

    @property
    def allowed(self):
    """ Returns the allowed value for this attribute """
        return self._allowed

    @property
    def range(self):
    """ Returns the range of the attribute """
        return self._range

    def has_flag(self, flag):
    """ Returns true if the attribute has the flag 'flag'

        :param flag: Flag that need to be ckecked
        :type flag: Flags
    """
        return (self._flags & flag) == flag

    def get_value(self):
    """ Returns the value of the attribute """
        return self._value

    def set_value(self, value):
    """ Change the value of the attribute after checking the type """
        valid = True

        if self.type == Types.Enumerate:
            valid = value in self._allowed

        if self.type in [Types.Double, Types.Integer] and self.range:
            (min, max) = self.range
            valid = (value >= min and value <= max) 
        
        valid = valid and self.is_valid_value(value)

        if valid: 
            if self.set_hook:
                # Hook receives old value, new value
                value = self.set_hook(self._value, value)

            self._value = value
        else:
            raise ValueError("Invalid value %s for attribute %s" %
                    (str(value), self.name))

    value = property(get_value, set_value)

    def is_valid_value(self, value):
        """ Attribute subclasses will override this method to add 
        adequate validation"""
        return True

