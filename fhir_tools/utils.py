# -*- coding: utf-8 -*-
# Copyright (c) 2019 Pavel 'Blane' Tuchin
import os
import json
from six.moves.urllib.parse import urlsplit

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
V4_DEF_PATH = os.path.join(BASE_PATH, 'definitions/v4')


def resource_from_path(path):
    index = path.find('.')
    if index == -1:
        return path
    return path[:index]


def resource_from_url(url):
    return urlsplit(url).path.split('/')[-1]


def get_bundle_entries(bundle):
    return (e['resource'] for e in bundle['entry'])


def read_resource_definitions(input_file):
    input_file = os.path.join(V4_DEF_PATH, 'official', input_file)
    with open(input_file) as fp:
        return json.load(fp)


def filter_structure_definitions(entries):
    return (e for e in entries if e['resourceType'] == 'StructureDefinition')


STRIPPED_KEYS = {'id', 'name', 'status', 'kind', 'abstract', 'type', 'baseDefinition', 'snapshot'}
STRIPPED_KEYS_ELEMENT = {'isModifier', 'min', 'max', 'base', 'isSummary', 'path', 'id', 'type'}


def strip_down_definitions_to_file(output=None):
    if output is None:
        output = os.path.join(V4_DEF_PATH, 'profiles-resources.stripped.json')
    res_defs = strip_down_definitions()
    with open(output, 'w') as out_fp:
        json.dump(list(res_defs), out_fp, indent=2)


def strip_down_definitions():
    def strip_keys(entry):
        res_def = {k: v for k, v in entry.items() if k in STRIPPED_KEYS}
        if 'snapshot' in res_def:
            elements = res_def['snapshot']['element']
            res_def['snapshot']['element'] = [strip_keys_element(e) for e in elements]
        return res_def

    def strip_keys_element(element):
        return {k: v for k, v in element.items() if k in STRIPPED_KEYS_ELEMENT}

    profiles = read_resource_definitions('profiles-resources.json')
    res_defs = get_bundle_entries(profiles)
    res_defs = filter_structure_definitions(res_defs)
    res_defs = (strip_keys(e) for e in res_defs)
    return res_defs
