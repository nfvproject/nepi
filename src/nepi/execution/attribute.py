"""
    NEPI, a framework to manage network experiments
    Copyright (C) 2013 INRIA

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""

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
    # Attribute is not modifiable by the user during runtime
    ExecReadOnly        = 0x02
    # Attribute is an access credential
    Credential      = 0x04

class Attribute(object):
    def __init__(self, name, help, type = Types.String,
            flags = Flags.NoFlags, default = None, allowed = None,
            set_hook = None):
        self._name = name
        self._help = help
        self._type = type
        self._flags = flags
        self._allowed = allowed
        self._default = self._value = default
        # callback to be invoked upon changing the 
        # attribute value
        self.set_hook = set_hook

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

    @property
    def allowed(self):
        return self._allowed

    def has_flag(self, flag):
        return (self._flags & flag) == flag

    def get_value(self):
        return self._value

    def set_value(self, value):
        valid = True

        if self.type == Types.Enum:
            valid = value in self._allowed
        
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

