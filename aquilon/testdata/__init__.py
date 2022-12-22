""" Module to provide test data for mocking pynetbox while unit testing """

from copy import deepcopy
from json import load
from types import SimpleNamespace

import pynetbox

def load_data():
    """ Loads fake objects from JSON files """
    result = SimpleNamespace()

    result.API = SimpleNamespace(
        base_url='http://netbox.example.org/api/',
        token='a8352bb6-75f5-4b6e-ad0e-3f21b8f0615b',
        session_key='42',
    )

    result.ENDPOINT = deepcopy(result.API)

    files = {
        'device_physical': pynetbox.models.dcim.Devices,
        'device_virtual': pynetbox.models.virtualization.VirtualMachines,
        'interfaces_physical': pynetbox.models.dcim.Interfaces,
        'interfaces_virtual': pynetbox.core.response.Record,
        'addresses_ipv4': pynetbox.models.ipam.IpAddresses,
        'addresses_ipv6': pynetbox.models.ipam.IpAddresses,
    }

    for name, model in files.items():
        with open(f'testdata/{name}.json', encoding='utf-8') as json_file:
            data = load(json_file)
            obj = None
            if isinstance(data, dict):
                # Just a single object
                obj = model(values=data, api=deepcopy(result.API), endpoint=deepcopy(result.ENDPOINT))
            elif isinstance(data, list):
                # List of objects emulating a RecordSet
                obj = [model(values=v, api=deepcopy(result.API), endpoint=deepcopy(result.ENDPOINT)) for v in data]
            setattr(result, name.upper(), obj)

    return result
