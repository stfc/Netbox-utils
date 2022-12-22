"""
Test cases for netbox2aquilon
"""

# pylint: disable=protected-access,missing-function-docstring

import json

from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch, mock_open

from netbox_dump_subnetdata import NetboxDumpSubnetdata

import testdata

FAKE = testdata.load_data()


def test__get_subnet_fields(mocker):
    test_obj = NetboxDumpSubnetdata()

    test_obj.netbox.ipam.prefixes = SimpleNamespace()
    test_obj.netbox.ipam.prefixes.filter = mocker.MagicMock(return_value=deepcopy(FAKE.PREFIXES_IPV4))

    subnets = test_obj._get_subnet_fields()
    assert len(subnets) == 7
    print(subnets)
    assert {s['SubnetAddress'] for s in subnets} == {
        "10.246.176.0",
        "10.6.0.0",
        "172.16.254.0",
        "192.168.176.0",
        "192.168.216.64",
        "192.168.232.0",
        "192.168.80.0",
    }


def test_write_subnetdata_txt(mocker):
    test_obj = NetboxDumpSubnetdata()

    test_obj.netbox.ipam.prefixes = SimpleNamespace()
    test_obj.netbox.ipam.prefixes.filter = mocker.MagicMock(return_value=deepcopy(FAKE.PREFIXES_IPV4))

    with patch("builtins.open", mock_open(read_data="data")) as mock_file:
        test_obj.write_subnetdata_txt('/tmp/fake_place')
    mock_file.assert_called_with("/tmp/fake_place/subnetdata.txt", 'w', encoding='utf-8')

    handle = mock_file()
    with open('testdata/subnetdata.txt', 'r', encoding='utf-8') as test_subnetdata:
        handle.writelines.assert_called_once_with(test_subnetdata.readlines())


def test_write_subnetdata_json(mocker):
    test_obj = NetboxDumpSubnetdata()

    test_obj.netbox.ipam.prefixes = SimpleNamespace()
    test_obj.netbox.ipam.prefixes.filter = mocker.MagicMock(return_value=deepcopy(FAKE.PREFIXES_IPV4))

    with open('testdata/subnetdata.json', 'r', encoding='utf-8') as test_subnetdata_file:
        test_subnetdata = json.load(test_subnetdata_file)

    mock_dump = mocker.patch.object(json, 'dump')
    with patch("builtins.open", mock_open(read_data="data")) as mock_file:
        test_obj.write_subnetdata_json('/tmp/fake_place')

    mock_file.assert_called_with("/tmp/fake_place/subnetdata.json", 'w', encoding='utf-8')

    mock_file_handle = mock_file()
    mock_dump.assert_called_with(test_subnetdata, mock_file_handle)
