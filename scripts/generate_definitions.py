# -*- coding: utf-8 -*-
# Copyright (c) 2019 Pavel 'Blane' Tuchin
import os
import sys

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
PROJECT_PATH = os.path.dirname(BASE_PATH)
sys.path.append(os.path.join(PROJECT_PATH))


def main():
    from fhir_tools.generation import generate_resource_definitions_to_file, generate_type_definitions_to_file
    generate_resource_definitions_to_file()
    generate_type_definitions_to_file()


if __name__ == '__main__':
    main()
