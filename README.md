# fhir_tools

Simple set of tools for working with FHIR resources and complex types.

Basic usage:

```python
from fhir_tools import readers
from fhir_tools import resources

definitions = readers.defs_from_generated()
resources = resources.Resources(definitions)

name = resources.HumanName(family='Doe', given=['John'], text='John Doe')
patient = resource.Patient(name=[name], id='example')

print(patient.name[0].text)
```
