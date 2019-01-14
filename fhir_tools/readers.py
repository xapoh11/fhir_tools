# -*- coding: utf-8 -*-
# Copyright (c) 2019 Pavel 'Blane' Tuchin
import json
from . import generation
from . import utils


def defs_from_generated(
        resources_file=generation.DEFAULT_RESOURCE_DEFS_FILE_NAME,
        types_file=generation.DEFAULT_TYPE_DEFS_FILE_NAME):
    resource_defs = resource_defs_from_generated(resources_file)
    type_defs = type_defs_from_generated(types_file)
    return resource_defs, type_defs


def resource_defs_from_generated(file_name=generation.DEFAULT_RESOURCE_DEFS_FILE_NAME):
    return _read_defs(file_name)


def type_defs_from_generated(file_name=generation.DEFAULT_TYPE_DEFS_FILE_NAME):
    return _read_defs(file_name)


def _read_defs(file_name):
    with open(file_name) as fp:
        defs = json.load(fp)
        return Definitions(defs)


class Definitions(object):
    def __init__(self, _json):
        self.defs = {k: StructDefinition(v) for k, v in _json.items()}

    def types_from_path(self, path):
        element = self.find_element(path)
        return element.types

    def find_element(self, path):
        name = utils.resource_from_path(path)
        resource = self.defs[name]
        return resource[path]


class StructDefinition(object):
    def __init__(self, _json):
        self.abstract = _json['abstract']
        self.base = _json['base']
        self.name = _json['name']
        elements = _json['elements']
        self.elements = {k: ElementDefinition(v) for k, v in elements.items()}


class ElementDefinition(object):
    def __init__(self, json):
        self.min = json['min']
        self.max = json['max']
        self.types = json['types']

    @property
    def is_unlimited(self):
        return self.max == '*'

    @property
    def is_single(self):
        return self.max == 1
