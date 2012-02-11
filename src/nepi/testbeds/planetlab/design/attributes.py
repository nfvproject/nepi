
from nepi.design.attributes import Attribute, AttributeTypes, is_valid_ipv4

class AddrListAttribute(Attribute):
    def __init__(self, name, help, default_value = None, 
            flags = None, tags = []):
        type = AttributeTypes.STRING
        super(AddrListAttribute, self).__init__(name, help, type, 
                default_value, flags, tags)

    def is_valid(self, value):
        invalid = False
        if not isinstance(value, str):
            invalid = True
        
        if not value:
            # No empty strings
            invalid = True
        
        components = value.split(',')
        
        for component in components:
            if '/' in component:
                addr, mask = component.split('/',1)
            else:
                addr, mask = component, '32'
        
        if mask is not None and not (mask and mask.isdigit()):
            # No empty or nonnumeric masks
            invalid = True
        
        if not is_ipv4(addr):
            # Address part must be ipv4
            invalid = True

        if invalid:
            self._logger.error("Wrong value %r for AddrListAttribute %s",
                str(value), self.name)
            return False
        return True

class PortListAttribute(Attribute):
    def __init__(self, name, help, default_value = None, 
            flags = None, tags = []):
        type = AttributeTypes.STRING
        super(PortListAttribute, self).__init__(name, help, type, 
                default_value, flags, tags)

    def is_valid(self, value):
        invalid = False
        if not isinstance(value, str):
            invalid = True
        
        if not value:
            # No empty strings
            invalid = True

        components = value.split(',')
        
        for component in components:
            if '-' in component:
                pfrom, pto = component.split('-',1)
            else:
                pfrom = pto = component
            
            if not pfrom or not pto or not pfrom.isdigit() or not pto.isdigit():
                # No empty or nonnumeric ports
                invalid = True

        if invalid:
            self._logger.error("Wrong value %r for PortListAttribute %s",
                str(value), self.name)
            return False
        return True

