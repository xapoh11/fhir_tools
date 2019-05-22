# -*- coding: utf-8 -*-
# Copyright (c) 2019 Pavel 'Blane' Tuchin
from __future__ import unicode_literals
import json
import six
from . import generation
from . import utils


RES_DEFS = generation.DEFAULT_RESOURCE_DEFS_FILE_NAME
TYPE_DEFS = generation.DEFAULT_TYPE_DEFS_FILE_NAME


def defs_from_generated(resources_file=RES_DEFS, types_file=TYPE_DEFS):
    """Create definitions from pre-generated resource and type definitions

    :param resources_file: path to pre-generated resource definitions file
    :param types_file: path to pre-generated type definitions file
    :return:
    """
    with open(resources_file) as res_fp, \
            open(types_file) as types_fp:
        res_defs = json.load(res_fp)
        type_defs = json.load(types_fp)
        return Definitions(res_defs, type_defs)


def defs_from_raw(resources_file='profiles-resources.json', types_file='profiles-types.json'):
    """Create definitions directly from profiles downloaded from FHIR official website

    :param resources_file: path to resources profiles
    :param types_file: path to types profiles
    :return:
    """
    res_defs = generation.generate_resource_definitions(resources_file)
    type_defs = generation.generate_type_definitions(types_file)
    return Definitions(res_defs, type_defs)


class Definitions(object):
    """Collection of definition FHIR Resources and Complex types.

    :ivar type_defs: dictionary of Complex Type definitions
    :ivar res_defs: dictionary of Resource definitions
    """
    def __init__(self, res_defs, type_defs):
        self.type_defs = {k: StructDefinition(v, type_defs) for k, v in type_defs.items()}
        self.res_defs = {k: StructDefinition(v, type_defs) for k, v in res_defs.items()}

    def types_from_path(self, path):
        """Get element types

        :param path: point-separated path to the element (can start with a resource or complex type)
        :return: type definitions for provided path
        """
        element = self.find(path)
        if element.is_struct_def:
            raise ValueError('Path does not point to an element')
        return element.types

    def find(self, path):
        """Find definition for provided path

        :param path: point-separated path to the element or resource
        :return: Either resource definition or element definition, depending on the path
        """
        name = utils.resource_from_path(path)
        resource = self.get_def(name)
        if name == path:
            return resource
        return resource[path]

    def get_def(self, name):
        """Get resource or complex type definition.

        Method will raise `KeyError` if definition is not found

        :param name: resource or complex type name
        :return: resource or complex type definition
        """
        try:
            return self.res_defs[name]
        except KeyError:
            return self.type_defs[name]


class StructDefinition(object):
    """Structure definition.

    Used to define a Resource or a Complex Type
    """
    def __init__(self, _json, type_defs):
        #: Is this a structure definition (yes, it is)
        self.is_struct_def = True
        #: Is this definition abstract
        self.abstract = _json['abstract']
        #: Name of the base definition
        self.base = _json['base']
        #: Definition name
        self.name = _json['name']
        elements = _json['elements']
        #: Dictionary of elements present in this definition
        self.elements = {k: ElementDefinition(v, type_defs) for k, v in elements.items()}


class ElementDefinition(object):
    """Definition of the element in Resource or Complex Type.

    :ivar max: maximum number of values in this element (`None` if unlimited)
    :ivar is_unlimited: can this element have unlimited number of values
    :ivar is_required: is this element required (min value is 1)
    :ivar is_single: is this element single (max == 1)
    :ivar is_array: is this element an array (opposite to `is_single`)
    :ivar types: types that are allowed in this element
    """
    def __init__(self, _json, type_defs):
        #: Is this a structure definition (no, it is not)
        self.is_struct_def = False

        #: Minimal number of values in this element
        self.min = _json['min']
        _max = _json['max']
        if _max == '*':
            self.max = None
            self.is_unlimited = True
        else:
            self.max = int(_max)
            self.is_unlimited = False
        self.is_required = self.min > 0
        self.is_single = self.max == 1
        self.is_array = not self.is_single

        self.types = [Type(t, type_defs) for t in _json['types']]

    @property
    def is_polymorphic(self):
        """Is this element polymorphic? (Can contain more than one type)

        :return: `True` if this element is polymorphic
        """
        return len(self.types) != 1

    @property
    def type(self):
        """Get a type definition of this element (only usable for non-polymorphic elements)

        :return: type definition of this element/
        """
        if self.is_polymorphic:
            raise ValueError('Element is polymorphic')
        return self.types[0]

    def to_single_type(self, _type):
        """Convert polymorphic element to a single type.

        :param _type: one of the polymorphic types
        :return: New element definition for a provided type
        :raises ValueError
        """
        if _type not in self.types:
            raise ValueError('Invalid Type')
        new_def = ElementDefinition({
            'min': self.min,
            'max': '*' if self.is_unlimited else six.text_type(self.max),
            'types': []
        }, {})
        new_def.types = [_type]
        return new_def


class Type(object):
    """Type definition.

    Contains necessary information about a type, that can be present in some element.

    :ivar code: type name (str)
    :ivar is_reference: is this type a reference
    :ivar is_backbone: is this type BackboneElement
    :ivar is_complex: is this a complex type
    :ivar is_primitive: is this a primitive type
    :ivar to: for a reference type - a list of targets, `None` otherwise
    :ivar is_any: if this type is a reference and list of targets is empty (can be any kind of resource)
    """
    def __init__(self, _json, type_defs):
        self.code = _json['code']
        self.is_reference = self.code == 'Reference'
        self.is_backbone = self.code == 'BackboneElement' or self.code == 'Element'
        self.is_resource = self.code == 'Resource'
        self.is_complex = self.code in type_defs
        self.is_primitive = not self.is_complex
        if self.is_reference:
            self.to = _json.get('targets')
            if not self.to:
                self.is_any = True
        else:
            self.to = None
            self.is_any = False
