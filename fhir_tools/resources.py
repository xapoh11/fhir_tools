# -*- coding: utf-8 -*-
# Copyright (c) 2019 Pavel 'Blane' Tuchin
from __future__ import unicode_literals
import six


class Resources(object):
    """Repository of generated classed for Resources, Complex Types and
    Backbone Elements

    """

    def __init__(self, definitions):
        self._definitions = definitions
        self._types = {}
        self._resources = {}
        for _type, definition in six.iteritems(definitions.type_defs):
            self._types[_type] = self._create_type(_type, definition)
        for resource, definition in six.iteritems(definitions.res_defs):
            self._resources[resource] = self._create_resource(
                resource, definition)

    def _create_type(self, name, definition):
        fields, polymorphic, backbones = self._create_fields(
            definition.elements)
        attrs = {
            b'_fhir_resources': self,
            b'_fhir_fields': fields,
            b'_fhir_polymorphic': polymorphic
        }
        attrs.update({bytes(k): v for k, v in six.iteritems(backbones)})
        return type(bytes(name), (Type, ), attrs)

    def _create_resource(self, name, definition):
        fields, polymorphic, backbones = self._create_fields(
            definition.elements)
        attrs = {
            b'_fhir_resources': self,
            b'_fhir_fields': fields,
            b'_fhir_polymorphic': polymorphic,
            b'_fhir_resource_type': name
        }
        attrs.update({bytes(k): v for k, v in six.iteritems(backbones)})
        return type(bytes(name), (Resource, ), attrs)

    def _create_backbone(self, name, elements):
        fields, polymorphic, backbones = self._create_fields(elements)
        attrs = {
            b'_fhir_resources': self,
            b'_fhir_fields': fields,
            b'_fhir_polymorphic': polymorphic,
        }
        attrs.update({bytes(k): v for k, v in six.iteritems(backbones)})
        return type(bytes(name), (Backbone, ), attrs)

    def _create_fields(self, elements):
        fields = {}
        polymorphic = {}
        backbones = {}
        for field, element_def, is_backbone in self._iter_elements(elements):
            # TODO: Handle backbone elements
            if is_backbone:
                name, _ = field.split('.', 1)
                if name not in backbones:
                    backbones[name] = {}
                backbones[name][field] = element_def
                continue

            if not field.endswith('[x]'):
                fields[field] = element_def
            else:
                field = field[:-3]
                poly_fields = set()
                for _type in element_def.types:
                    name = field + to_camel_case(_type.code)
                    fields[name] = element_def.to_single_type(_type)
                    poly_fields.add(name)
                polymorphic[field] = poly_fields

        backbone_types = {}
        for name, elements in backbones.items():
            name = to_camel_case(name)
            backbone_types[name] = self._create_backbone(name, elements)
        return fields, polymorphic, backbone_types

    @staticmethod
    def _iter_elements(elements):
        for path, element_def in six.iteritems(elements):
            _, field = path.split('.', 1)
            is_backbone = '.' in field
            yield field, element_def, is_backbone

    def get(self, name):
        """Get a class from repository by name

        Name can be a Resource, a Complex Type or a Backbone Element

        :param name: name of a class (str).
        :return: Class for a provided name
        """
        if name in self._resources:
            return self._resources[name]
        if name in self._types:
            return self._types[name]
        raise KeyError('Class not found')

    def from_json(self, json):
        _class = self.get(json['resourceType'])
        return _class.from_json(json)

    def from_db_json(self, json, convert_to_fhir=True):
        _class = self.get(json['resourceType'])
        resource = _class.from_db_json(json)
        if convert_to_fhir:
            resource.to_fhir_format()
        return resource

    def __getattr__(self, name):
        return self.get(name)


class FHIRObject(dict):
    _fhir_resources = None
    _fhir_fields = {}
    _fhir_polymorphic = {}

    def __init__(self, **kwargs):
        initial = {
            k: v
            for k, v in six.iteritems(kwargs) if (k in self._fhir_fields) and (
                v is not None) and not (isinstance(v, list) and not v)
        }
        dict.__init__(self, **initial)

    def __getattr__(self, name):
        if name in self._fhir_polymorphic:
            if name in self:
                # DB format
                return self[name]
            for _name in self._fhir_polymorphic[name]:
                if _name in self:
                    return self[_name]
            else:
                raise AttributeError(name)
        if name in self._fhir_fields and name in self:
            return self[name]
        raise AttributeError(name)

    def __setattr__(self, name, value):
        if name not in self._fhir_fields:
            raise AttributeError(name)

        if value is None or (isinstance(value, list) and not value):
            try:
                self.__delattr__(name)
            except (AttributeError, KeyError):
                pass
        else:
            self[name] = value

    def __delattr__(self, name):
        del self[name]

    @classmethod
    def from_json(cls, json):
        """Creates FHIR object (Resource, Complex Type or BackboneElement)

        :param json: parsed JSON (dict)
        :return: FHIR object created from JSON
        """
        kwargs = {}
        for field, value in six.iteritems(json):
            if field not in cls._fhir_fields:
                continue
            element = cls._fhir_fields[field]
            if not element.type.is_complex and not element.type.is_backbone:
                if element.type.is_resource:
                    kwargs[field] = cls._fhir_resources.from_json(value)
                else:
                    kwargs[field] = value
            else:
                if element.type.is_backbone:
                    _class = getattr(cls, to_camel_case(field))
                else:
                    _class = cls._fhir_resources.get(element.type.code)
                if element.is_array:
                    kwargs[field] = [_class.from_json(v) for v in value]
                else:
                    kwargs[field] = _class.from_json(value)

        return cls(**kwargs)

    @classmethod
    def from_db_json(cls, json):
        """Creates FHIR object (Resource, Complex Type or BackboneElement).

        References and polymorphic fields are expected to be in a DB friendly
        format.
        See FHIRBase documentation for details.

        :param json: parsed JSON (dict)
        :return: FHIR object created from JSON
        """
        kwargs = {}
        poly_fields = {}
        for field, value in six.iteritems(json):
            if field in cls._fhir_polymorphic:
                # Leave polymorphic types unchanged when converting from DB
                # format
                poly_fields[field] = value
            if field not in cls._fhir_fields:
                continue
            element = cls._fhir_fields[field]
            if not element.type.is_complex and not element.type.is_backbone:
                if element.type.is_resource:
                    kwargs[field] = cls._fhir_resources.from_db_json(value)
                else:
                    kwargs[field] = value
            else:
                if element.type.is_backbone:
                    _class = getattr(cls, to_camel_case(field))
                else:
                    if element.type.is_reference:
                        _class = DBReference
                    else:
                        _class = cls._fhir_resources.get(element.type.code)
                if element.is_array:
                    kwargs[field] = [_class.from_db_json(v) for v in value]
                else:
                    kwargs[field] = _class.from_db_json(value)

        resource = cls(**kwargs)
        resource.update(poly_fields)
        return resource

    def to_db_format(self):
        """Convert FHIR Object to a DB friendly format."""
        converted = {}
        for field, value in six.iteritems(self):
            if field not in self._fhir_fields:
                continue
            element = self._fhir_fields[field]
            if element.type.is_reference:
                if element.is_array:
                    converted[field] = [
                        DBReference.from_reference(r) for r in value
                    ]
                else:
                    db_ref = DBReference.from_reference(value)
                    converted[field] = db_ref
            elif element.type.is_backbone or element.type.is_complex:
                if element.is_array:
                    [v.to_db_format() for v in value]
                else:
                    value.to_db_format()
        for poly_field, names in six.iteritems(self._fhir_polymorphic):
            for name in names:
                if name not in self:
                    continue
                element = self._fhir_fields[name]
                value = self.pop(name)
                converted[poly_field] = {element.type.code: value}
        self.update(converted)

    def to_fhir_format(self):
        """Convert FHIR Object to a default FHIR representation from DB
        friendly format.
        """

        def _convert_ref(val):
            ref = self._fhir_resources.Reference(
                reference='{}/{}'.format(val.resource_type, val.id))
            if 'display' in val:
                ref.display = val.display
            return ref

        converted = {}
        for field, value in six.iteritems(self):
            if field not in self._fhir_fields:
                continue
            element = self._fhir_fields[field]
            if element.type.is_reference:
                if element.is_array:
                    converted[field] = [_convert_ref(r) for r in value]
                else:
                    converted[field] = _convert_ref(value)
            elif element.type.is_backbone or element.type.is_complex:
                if element.is_array:
                    [v.to_fhir_format() for v in value]
                else:
                    value.to_fhir_format()
        for poly_field in six.iterkeys(self._fhir_polymorphic):
            if poly_field not in self:
                continue
            value = self.pop(poly_field)
            type_code, value = value.popitem()
            field_name = poly_field + to_camel_case(type_code)
            try:
                _class = self._fhir_resources.get(type_code)
            except KeyError:
                # Primitive value
                converted[field_name] = value
            else:
                converted[field_name] = _class.from_json(value)
        self.update(converted)

    def replace_refs(self, old, new):
        def _convert_ref(val):
            if 'reference' in val and val.reference == old:
                value.reference = new

        for field, value in six.iteritems(self):
            if field not in self._fhir_fields:
                continue
            element = self._fhir_fields[field]
            if element.type.is_reference:
                if element.is_array:
                    [_convert_ref(r) for r in value]
                else:
                    _convert_ref(value)
            elif element.type.is_backbone or element.type.is_complex:
                if element.is_array:
                    [v.replace_refs(old, new) for v in value]
                else:
                    value.replace_refs(old, new)


class Type(FHIRObject):
    pass


class Backbone(FHIRObject):
    pass


class Resource(FHIRObject):
    _fhir_resource_type = None

    def __init__(self, **kwargs):
        FHIRObject.__init__(self, **kwargs)
        self['resourceType'] = self._fhir_resource_type


class DBReference(dict):
    @classmethod
    def from_json(cls, json):
        return cls(**json)

    @classmethod
    def from_db_json(cls, json):
        return cls.from_json(json)

    @classmethod
    def from_reference(cls, reference):
        parts = reference.reference.split('/')
        if len(parts) > 2:
            raise ValueError('Non-local reference: {}'.format(
                reference.reference))
        resource_type, _id = parts
        ref = cls(resourceType=resource_type, id=_id)
        if hasattr(reference, 'display'):
            ref.display = reference.display
        return ref

    @property
    def resource_type(self):
        return self['resourceType']

    @resource_type.setter
    def resource_type(self, value):
        self['resourceType'] = value

    @property
    def id(self):
        return self['id']

    @id.setter
    def id(self, value):
        self['id'] = value

    @property
    def display(self):
        return self['display']

    @display.setter
    def display(self, value):
        self['display'] = value


def to_camel_case(name):
    return name[:1].capitalize() + name[1:]
