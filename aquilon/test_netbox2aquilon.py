"""
Test cases for netbox2aquilon
"""

# pylint: disable=protected-access,missing-function-docstring

import subprocess

from copy import deepcopy
from types import SimpleNamespace

from netbox2aquilon import Netbox2Aquilon

import testdata

FAKE = testdata.load_data()


def test_get_current_sandbox(mocker):
    test_obj = Netbox2Aquilon()

    # git rev-parse succeeds
    mocker.patch.object(subprocess, 'run', return_value=SimpleNamespace(
        returncode=0,
        stdout=b'/var/quattor/templates/abc12345/my_sandbox',
        stderr=b'',
    ))
    assert test_obj.get_current_sandbox() == 'abc12345/my_sandbox'

    # git rev-parse succeeds, but the path returned isn't deep enough to be a sandbox
    mocker.patch.object(subprocess, 'run', return_value=SimpleNamespace(
        returncode=0,
        stdout=b'/opt',
        stderr=b'',
    ))
    assert test_obj.get_current_sandbox() is None

    # git rev-parse fails
    mocker.patch.object(subprocess, 'run', return_value=SimpleNamespace(
        returncode=128,
        stdout=b'',
        stderr=b'fatal: Not a git repository (or any parent up to mount point /var/quattor)',
    ))
    assert test_obj.get_current_sandbox() is None


def test__netbox_copy_interfaces(mocker):
    test_obj = Netbox2Aquilon()

    # Physical devices with a management interface
    fake_device = SimpleNamespace(
        aq_machine_name='system7592',
    )
    test_obj.get_interfaces_from_device = mocker.MagicMock(return_value=deepcopy(FAKE.INTERFACES_PHYSICAL[:-1]))
    assert set(test_obj._netbox_copy_interfaces(fake_device)) == {
        'add_interface --machine system7592 --mac A1:B2:C3:D4:E5:3F --interface bmc0 --iftype management',
        'add_interface --machine system7592 --mac A1:B2:C3:D4:E5:DA --interface eth0',
        'add_interface --machine system7592 --mac A1:B2:C3:D4:E5:DB --interface eth1',
        'update_interface --machine system7592 --interface eth0 --boot',
    }

    # Virtual machine with two interfaces
    fake_device = SimpleNamespace(
        aq_machine_name='system6690',
    )
    test_obj.get_interfaces_from_device = mocker.MagicMock(return_value=deepcopy(FAKE.INTERFACES_VIRTUAL))
    assert set(test_obj._netbox_copy_interfaces(fake_device)) == {
        'add_interface --machine system6690 --mac A1:B2:C3:D4:E5:1B --interface eth0',
        'add_interface --machine system6690 --mac A1:B2:C3:D4:E5:99 --interface eth1',
        'update_interface --machine system6690 --interface eth0 --boot',
    }


def test__netbox_copy_addresses(mocker):
    test_obj = Netbox2Aquilon()

    fake_device = FAKE.DEVICE_PHYSICAL
    fake_device.aq_machine_name = 'system7592'

    # No addresses on an interface
    test_obj.get_interfaces_from_device = mocker.MagicMock(return_value=[deepcopy(FAKE.INTERFACES_PHYSICAL)[1]])
    test_obj.get_addresses_from_interface = mocker.MagicMock(return_value=[])
    assert set(test_obj._netbox_copy_addresses(fake_device)) == set([])

    # Addresses on an interface
    test_obj.get_interfaces_from_device = mocker.MagicMock(return_value=[deepcopy(FAKE.INTERFACES_PHYSICAL[1])])
    test_obj.get_addresses_from_interface = mocker.MagicMock(return_value=deepcopy(FAKE.ADDRESSES_IPV4))
    assert set(test_obj._netbox_copy_addresses(fake_device)) == set([
        'add_interface_address --machine system7592 --interface eth0 --ip 192.168.180.13 --fqdn aquilon.example.org',
    ])
