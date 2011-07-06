#!/usr/bin/env python
# -*- coding: utf-8 -*-

from nepi.core.attributes import AttributesMap, Attribute
from nepi.util import tags
from nepi.util.tags import Taggable

class AddressableMixin(object):
    def __init__(self, guid, factory, testbed_guid, container = None):
        super(AddressableMixin, self).__init__(guid, factory, testbed_guid, 
                container)
        max_addr = self._factory_attributes["maxAddresses"]
        self._max_addresses = max_addr
        self._addresses = list()

    @property
    def addresses(self):
        return self._addresses

    @property
    def max_addresses(self):
        return self._max_addresses

class UserAddressableMixin(AddressableMixin):
    def __init__(self, guid, factory, testbed_guid, container = None):
        super(UserAddressableMixin, self).__init__(guid, factory, testbed_guid, 
                container)

    def add_address(self):
        if len(self._addresses) == self.max_addresses:
            raise RuntimeError("Maximun number of addresses for this box reached.")
        from nepi.core.design import Address
        address = Address()
        self._addresses.append(address)
        return address

    def delete_address(self, address):
        self._addresses.remove(address)
        del address

    def destroy(self):
        super(UserAddressableMixin, self).destroy()
        for address in list(self.addresses):
            self.delete_address(address)
        self._addresses = None

class RoutableMixin(object):
    def __init__(self, guid, factory, testbed_guid, container = None):
        super(RoutableMixin, self).__init__(guid, factory, testbed_guid, 
            container)
        self._routes = list()

    @property
    def routes(self):
        return self._routes

class UserRoutableMixin(RoutableMixin):
    def __init__(self, guid, factory, testbed_guid, container = None):
        super(UserRoutableMixin, self).__init__(guid, factory, testbed_guid, 
            container)

    def add_route(self):
        from nepi.core.design import Route
        route = Route()
        self._routes.append(route)
        return route

    def delete_route(self, route):
        self._routes.remove(route)
        del route

    def destroy(self):
        super(UserRoutableMixin, self).destroy()
        for route in list(self.routes):
            self.delete_route(route)
        self._route = None

def MixIn(MyClass, MixIn):
    # Mixins are installed BEFORE "Box" because
    # Box inherits from non-cooperative classes,
    # so the MRO chain gets broken when it gets
    # to Box.

    # Install mixin
    MyClass.__bases__ = (MixIn,) + MyClass.__bases__
    
    # Add properties
    # Somehow it doesn't work automatically
    for name in dir(MixIn):
        prop = getattr(MixIn,name,None)
        if isinstance(prop, property):
            setattr(MyClass, name, prop)
    
    # Update name
    MyClass.__name__ = MyClass.__name__.replace(
        'Box',
        MixIn.__name__.replace('MixIn','')+'Box',
        1)

class Factory(AttributesMap, Taggable):
    _box_class_cache = {}

    def __init__(self, factory_id,
            create_function, 
            start_function, 
            stop_function, 
            status_function, 
            configure_function, 
            preconfigure_function,
            prestart_function,
            help = None,
            category = None):

        super(Factory, self).__init__()

        self._factory_id = factory_id
        self._create_function = create_function
        self._start_function = start_function
        self._stop_function = stop_function
        self._status_function = status_function
        self._configure_function = configure_function
        self._preconfigure_function = preconfigure_function
        self._prestart_function = prestart_function
        self._help = help
        self._category = category
        self._connector_types = dict()
        self._traces = dict()
        self._box_attributes = AttributesMap()
        self._factory = None

    @property
    def factory(self):
        if self._factory:
            return self._factory

        from nepi.core.design import Box

        if not self.has_addresses and not self.has_routes:
            self._factory = Box
        else:
            addresses = 'w' if self.allow_addresses else ('r' if self.has_addresses else '-')
            routes    = 'w' if self.allow_routes else ('r' if self.has_routes else '-')
            key = addresses+routes
            
            if key in self._box_class_cache:
                self._factory = self._box_class_cache[key]
            else:
                # Create base class
                class _factory(Box):
                    def __init__(self, guid, factory, testbed_guid, container = None):
                        super(_factory, self).__init__(guid, factory, testbed_guid, container)
                
                # Add mixins, one by one
                if self.allow_addresses:
                    MixIn(_factory, UserAddressableMixin)
                elif self.has_addresses:
                    MixIn(_factory, AddressableMixin)
                    
                if self.allow_routes:
                    MixIn(_factory, UserRoutableMixin)
                elif self.has_routes:
                    MixIn(_factory, RoutableMixin)
                
                # Put into cache
                self._box_class_cache[key] = self._factory = _factory
        return self._factory

    @property
    def factory_id(self):
        return self._factory_id

    @property
    def allow_addresses(self):
        return self.has_tag(tags.ALLOW_ADDRESSES)

    @property
    def allow_routes(self):
        return self.has_tag(tags.ALLOW_ROUTES)

    @property
    def has_addresses(self):
        return self.has_tag(tags.HAS_ADDRESSES) or \
                self.allow_addresses

    @property
    def has_routes(self):
        return self.has_tag(tags.HAS_ROUTES) or \
                self.allow_routes

    @property
    def help(self):
        return self._help

    @property
    def category(self):
        return self._category

    @property
    def connector_types(self):
        return self._connector_types.values()

    @property
    def traces(self):
        return self._traces.values()

    @property
    def traces_list(self):
        return self._traces.keys()

    @property
    def box_attributes(self):
        return self._box_attributes

    @property
    def create_function(self):
        return self._create_function

    @property
    def prestart_function(self):
        return self._prestart_function

    @property
    def start_function(self):
        return self._start_function

    @property
    def stop_function(self):
        return self._stop_function

    @property
    def status_function(self):
        return self._status_function

    @property
    def configure_function(self):
        return self._configure_function

    @property
    def preconfigure_function(self):
        return self._preconfigure_function

    def connector_type(self, name):
        return self._connector_types[name]

    def add_connector_type(self, connector_type):
        self._connector_types[connector_type.name] = connector_type

    def add_trace(self, name, help, enabled = False):
        self._traces[name] = (name, help, enabled)

    def add_box_attribute(self, name, help, type, value = None, range = None,
        allowed = None, flags = Attribute.NoFlags, validation_function = None,
        category = None):
        self._box_attributes.add_attribute(name, help, type, value, range,
                allowed, flags, validation_function, category)

    def create(self, guid, testbed_description):
        return self.factory(guid, self, testbed_description.guid)

    def destroy(self):
        super(Factory, self).destroy()
        self._connector_types = None

