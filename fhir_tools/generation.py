# -*- coding: utf-8 -*-
# Copyright (c) 2019 Pavel 'Blane' Tuchin

from __future__ import unicode_literals, absolute_import
import json
import os

from . import utils


GENERATED_PATH = os.path.join(utils.V4_DEF_PATH, 'generated')
DEFAULT_RESOURCE_DEFS_FILE_NAME = os.path.join(GENERATED_PATH, 'resources.json')
DEFAULT_TYPE_DEFS_FILE_NAME = os.path.join(GENERATED_PATH, 'types.json')


def generate_resource_definitions_to_file(
        input_file='profiles-resources.json',
        output_file=DEFAULT_RESOURCE_DEFS_FILE_NAME):
    transformed = generate_resource_definitions(input_file)
    with open(output_file, 'w') as out_fp:
        json.dump(transformed, out_fp, indent=2)


def generate_type_definitions_to_file(
        input_file='profiles-types.json',
        output_file=DEFAULT_TYPE_DEFS_FILE_NAME):
    transformed = generate_type_definitions(input_file)
    with open(output_file, 'w') as out_fp:
        json.dump(transformed, out_fp, indent=2)


def generate_resource_definitions(input_file='profiles-resources.json'):
    bundle = utils.read_resource_definitions(input_file)
    entries = utils.get_bundle_entries(bundle)
    definitions = utils.filter_structure_definitions(entries)
    transformed = transform_definitions(definitions)
    return transformed


def generate_type_definitions(input_file='profiles-types.json'):
    bundle = utils.read_resource_definitions(input_file)
    entries = utils.get_bundle_entries(bundle)
    entries = utils.filter_structure_definitions(entries)
    definitions = filter_primitive_types(entries)
    transformed = transform_definitions(definitions)
    return transformed


def transform_definitions(definitions):
    result = {}
    for definition in definitions:
        status = definition.get('status')
        if status != 'active' and status != 'draft':
            continue  # We only care about active ones or draft

        if 'baseDefinition' in definition:
            base = utils.resource_from_url(definition['baseDefinition'])
        else:
            base = None
        name = definition['name']
        abstract = definition['abstract']
        elements = definition['snapshot']['element']
        result[name] = {
            'name': name,
            'abstract': abstract,
            'base': base,
            'elements': transform_elements(elements)
        }
    return result


def transform_elements(elements):
    results = {}
    for element in elements:
        path = element['path']
        if '.' not in path:
            continue  # Root element (don't care about it)
        _min = element.get('min', 0)
        _max = element.get('max', '*')
        types = element.get('type', [])
        results[path] = {
            'min': _min,
            'max': _max,
            'types': list(transform_types(types))
        }
    return results


def transform_types(types):
    for _type in types:
        if 'code' not in _type:
            continue
        code = _type['code']
        result = {'code': code}
        if code == 'Reference' and 'targetProfile' in _type:
            targets = [utils.resource_from_url(r) for r in _type['targetProfile']]
            result['targets'] = targets
        yield result


def filter_primitive_types(entries):
    return (e for e in entries if e.get('kind') != 'primitive-type')
