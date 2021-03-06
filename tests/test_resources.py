# -*- coding: utf-8 -*-
# Copyright (c) 2019 Pavel 'Blane' Tuchin
from __future__ import unicode_literals
import unittest

from fhir_tools import readers
from fhir_tools import resources


class TestResources(unittest.TestCase):
    def setUp(self):
        self.definitions = readers.defs_from_generated()
        self.resources = resources.Resources(self.definitions)

    def tearDown(self):
        self.definitions = None
        self.resources = None

    def test_type(self):
        self.assertTrue(issubclass(self.resources.Patient, resources.Resource))
        self.assertTrue(issubclass(self.resources.HumanName, resources.Type))

    def test_attributes(self):
        patient = self.resources.Patient(id='example')
        self.assertEqual(patient.id, 'example')
        self.assertEqual(patient['resourceType'], 'Patient')

    def test_from_json(self):
        patient = self.resources.Patient.from_json({
            'id':
            'example',
            'name': [{
                'given': ['John'],
                'family': 'Doe',
                'text': 'John Doe'
            }],
            'contact': [{
                'gender': 'male'
            }]
        })
        self.assertEqual(patient.id, 'example')
        self.assertIsInstance(patient.name[0], self.resources.HumanName)
        self.assertIsInstance(patient.contact[0],
                              self.resources.Patient.Contact)
        self.assertEqual(patient.name[0].family, 'Doe')
        self.assertEqual(patient.contact[0].gender, 'male')

    def test_from_json_cls_method(self):
        patient = self.resources.from_json({
            'resourceType':
            'Patient',
            'id':
            'example',
            'name': [{
                'given': ['John'],
                'family': 'Doe',
                'text': 'John Doe'
            }],
            'contact': [{
                'gender': 'male'
            }]
        })
        self.assertEqual(patient.id, 'example')
        self.assertIsInstance(patient.name[0], self.resources.HumanName)
        self.assertIsInstance(patient.contact[0],
                              self.resources.Patient.Contact)
        self.assertEqual(patient.name[0].family, 'Doe')
        self.assertEqual(patient.contact[0].gender, 'male')

    def test_from_db_json(self):
        patient = self.resources.Patient.from_db_json({
            'id':
            'example',
            'name': [{
                'given': ['John'],
                'family': 'Doe',
                'text': 'John Doe'
            }],
            'deceased': {
                'boolean': False
            },
            'generalPractitioner': [{
                'id': 'example',
                'resourceType': 'Practitioner'
            }]
        })
        self.assertEqual(patient.id, 'example')
        self.assertIsInstance(patient.name[0], self.resources.HumanName)
        self.assertEqual(patient.name[0].family, 'Doe')
        self.assertIsInstance(patient.generalPractitioner[0],
                              resources.DBReference)
        self.assertEqual(patient.generalPractitioner[0].id, 'example')
        patient.to_fhir_format()
        self.assertEqual(patient.generalPractitioner[0].reference,
                         'Practitioner/example')
        self.assertEqual(patient.deceased, False)

    def test_from_db_json_cls_method_no_convert(self):
        patient = self.resources.from_db_json(
            {
                'resourceType':
                'Patient',
                'id':
                'example',
                'name': [{
                    'given': ['John'],
                    'family': 'Doe',
                    'text': 'John Doe'
                }],
                'deceased': {
                    'boolean': False
                },
                'generalPractitioner': [{
                    'id': 'example',
                    'resourceType': 'Practitioner'
                }]
            }, False)
        self.assertEqual(patient.id, 'example')
        self.assertIsInstance(patient.name[0], self.resources.HumanName)
        self.assertEqual(patient.name[0].family, 'Doe')
        self.assertIsInstance(patient.generalPractitioner[0],
                              resources.DBReference)
        self.assertEqual(patient.generalPractitioner[0].id, 'example')

    def test_from_db_json_cls_method(self):
        patient = self.resources.from_db_json({
            'resourceType':
            'Patient',
            'id':
            'example',
            'name': [{
                'given': ['John'],
                'family': 'Doe',
                'text': 'John Doe'
            }],
            'deceased': {
                'boolean': False
            },
            'generalPractitioner': [{
                'id': 'example',
                'resourceType': 'Practitioner'
            }]
        })
        self.assertEqual(patient.generalPractitioner[0].reference,
                         'Practitioner/example')

    def test_polymorphic(self):
        patient = self.resources.Patient(id='example', deceasedBoolean=True)
        self.assertEqual(patient.deceasedBoolean, True)
        self.assertEqual(patient.deceased, True)

    def test_backbone(self):
        self.assertTrue(
            issubclass(self.resources.Patient.Contact, resources.Backbone))
        contact = self.resources.Patient.Contact(gender='male')
        self.assertEqual(contact.gender, 'male')

    def test_backbone_in_backbone(self):
        self.assertTrue(
            issubclass(self.resources.InsurancePlan.Plan, resources.Backbone))
        self.assertTrue(
            issubclass(self.resources.InsurancePlan.Plan.GeneralCost,
                       resources.Backbone))
        plan = self.resources.InsurancePlan.Plan(generalCost=[
            self.resources.InsurancePlan.Plan.GeneralCost(comment='example')
        ])
        self.assertEqual(plan.generalCost[0].comment, 'example')

    def test_complex_type(self):
        name = self.resources.HumanName(family='Doe',
                                        given=['John'],
                                        text='John Doe')
        self.assertEqual(name.family, 'Doe')
        self.assertEqual(name.given[0], 'John')
        self.assertEqual(name.text, 'John Doe')

    def test_db_reference(self):
        reference = self.resources.Reference(display='Example',
                                             reference='Patient/example')
        db_reference = resources.DBReference.from_reference(reference)
        self.assertEqual(db_reference.display, 'Example')
        self.assertEqual(db_reference.id, 'example')
        self.assertEqual(db_reference.resource_type, 'Patient')

    def test_db_polymorphic(self):
        patient = self.resources.Patient.from_json({
            'id':
            'example',
            'name': [{
                'given': ['John'],
                'family': 'Doe',
                'text': 'John Doe'
            }],
            'deceasedBoolean':
            False,
        })
        patient.to_db_format()
        self.assertEqual(patient['deceased']['boolean'], False)

    def test_resource_type(self):
        bundle = self.resources.from_json({
            'resourceType':
            'Bundle',
            'type':
            'collection',
            'entry': [{
                'resource': {
                    'resourceType':
                    'Patient',
                    'id':
                    'example',
                    'name': [{
                        'given': ['John'],
                        'family': 'Doe',
                        'text': 'John Doe'
                    }],
                    'deceasedBoolean':
                    False,
                }
            }]
        })
        self.assertIsInstance(bundle.entry[0].resource, self.resources.Patient)

    def test_delete_attr_with_none(self):
        patient = self.resources.Patient(active=True)
        patient.active = None
        self.assertRaises(AttributeError, lambda: patient.active)
        patient.name = [{'family': 'Doe'}]
        patient.name = []
        self.assertRaises(AttributeError, lambda: patient.name)

    def test_extensions(self):
        patient = self.resources.Patient.from_json({
            'id': 'example',
            'name': [{
                'given': ['John'],
                'family': 'Doe',
                'text': 'John Doe'
            }],
            'extension': [{
                'url': 'http://example/extension',
                'valueString': 'example'
            }]
        })
        self.assertIsInstance(patient.extension[0], self.resources.Extension)
        extension = patient.extension[0]
        self.assertEqual(extension.url, 'http://example/extension')
        self.assertEqual(extension.value, 'example')

    def test_nested_extensions(self):
        patient = self.resources.Patient.from_json({
            'id': 'example',
            'name': [{
                'given': ['John'],
                'family': 'Doe',
                'text': 'John Doe'
            }],
            'extension': [{
                'url': 'http://example/extension',
                'extension': [{
                    'url': 'key',
                    'valueString': 'test'
                }, {
                    'url': 'value',
                    'valueString': 'testValue'
                }]
            }]
        })
        extension = patient.extension[0]
        extension_key = extension.extension[0]
        extension_value = extension.extension[1]
        self.assertEqual(extension_key.url, 'key')
        self.assertEqual(extension_key.value, 'test')
        self.assertEqual(extension_value.url, 'value')
        self.assertEqual(extension_value.value, 'testValue')
