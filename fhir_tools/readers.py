# -*- coding: utf-8 -*-
# Copyright (c) 2019 Pavel 'Blane' Tuchin
import json
import six
from . import generation
from . import utils


RES_DEFS = generation.DEFAULT_RESOURCE_DEFS_FILE_NAME
TYPE_DEFS = generation.DEFAULT_TYPE_DEFS_FILE_NAME


def defs_from_generated(resources_file=RES_DEFS, types_file=TYPE_DEFS):
    with open(resources_file) as res_fp, \
            open(types_file) as types_fp:
        res_defs = json.load(res_fp)
        type_defs = json.load(types_fp)
        return Definitions(res_defs, type_defs)


def defs_from_raw(resources_file='profiles-resources.json', types_file='profiles-types.json'):
    res_defs = generation.generate_resource_definitions(resources_file)
    type_defs = generation.generate_type_definitions(types_file)
    return Definitions(res_defs, type_defs)


class Definitions(object):
    def __init__(self, res_defs, type_defs):
        self.type_defs = {k: StructDefinition(v, type_defs) for k, v in type_defs.items()}
        self.res_defs = {k: StructDefinition(v, type_defs) for k, v in res_defs.items()}

    def types_from_path(self, path):
        element = self.find(path)
        if element.is_struct_def:
            raise ValueError('Path does not point to an element')
        return element.types

    def find(self, path):
        name = utils.resource_from_path(path)
        resource = self.get_def(name)
        if name == path:
            return resource
        return resource[path]

    def get_def(self, name):
        try:
            return self.res_defs[name]
        except KeyError:
            return self.type_defs[name]


class StructDefinition(object):
    def __init__(self, _json, type_defs):
        self.abstract = _json['abstract']
        self.base = _json['base']
        self.name = _json['name']
        elements = _json['elements']
        self.elements = {k: ElementDefinition(v, type_defs) for k, v in elements.items()}

    @property
    def is_struct_def(self):
        return True


class ElementDefinition(object):
    def __init__(self, _json, type_defs):
        self.is_struct_def = False

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
        return len(self.types) != 1

    @property
    def type(self):
        if self.is_polymorphic:
            raise ValueError('Element is polymorphic')
        return self.types[0]

    def to_single_type(self, _type):
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
    def __init__(self, _json, type_defs):
        self.code = _json['code']
        self.is_reference = self.code == 'Reference'
        self.is_backbone = self.code == 'BackboneElement'
        self.is_complex = self.code in type_defs
        self.is_primitive = not self.is_complex
        if self.is_reference:
            self.to = _json.get('targets')
            if not self.to:
                self.is_any = True
        else:
            self.to = None
            self.is_any = False
