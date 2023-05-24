"""
Test cases for core library
"""

# pylint: disable=protected-access

import logging

from copy import deepcopy
from types import SimpleNamespace

import pytest

from scd_netbox import SCDNetbox

import testdata

FAKE = testdata.load_data()


def test_get_device_by_name_or_magdb_id(mocker):
    """
    Test that get_device_by_name and get_device_by_magdb_id return unmodified objects.
    These are simple wrappers that should either pass objects through or error out.
    """
    scd_netbox = SCDNetbox()

    # The magic of pynetbox endpoints means we need to overwrite the parent object to prevent API calls happening
    # Using SimpleNamespace allows us to assign to any property without initialising a more complex structure
    scd_netbox.netbox.dcim.devices = SimpleNamespace()

    for method in [scd_netbox.get_device_by_name, scd_netbox.get_device_by_magdb_id]:
        scd_netbox.netbox.dcim.devices.get = mocker.MagicMock(return_value=42)
        assert 42 == method('foo')

        scd_netbox.netbox.dcim.devices.get = mocker.MagicMock(return_value='2112')
        assert '2112' == method('bar')

        # Should log an error and exit if nothing is found
        scd_netbox.netbox.dcim.devices.get = mocker.MagicMock(return_value=None)
        mocked_error = mocker.patch.object(logging, 'error')
        with pytest.raises(SystemExit):
            method('nothing')
        mocked_error.assert_called()


def test_get_device_by_hostname(mocker):
    """
    Test get_device_by_hostname
    """
    scd_netbox = SCDNetbox()

    fake_address_physical = SimpleNamespace(
        assigned_object_type='dcim.interface',
        assigned_object=SimpleNamespace(
            device=SimpleNamespace(
                id=277636,
            ),
        ),
    )

    fake_address_virtual = SimpleNamespace(
        assigned_object_type='virtualization.vminterface',
        assigned_object=SimpleNamespace(
            virtual_machine=SimpleNamespace(
                id=6465,
            ),
        ),
    )

    fake_address_garbage = SimpleNamespace(
        assigned_object_type='foobar.interface',
        assigned_object=SimpleNamespace(
            device=SimpleNamespace(
                id=53791,
            ),
        ),
    )

    # Overwrite the endpoints we're going to use
    scd_netbox.netbox.ipam.ip_addresses = SimpleNamespace()
    scd_netbox.netbox.dcim.devices = SimpleNamespace()
    scd_netbox.netbox.virtualization.virtual_machines = SimpleNamespace()

    # Test a physical interface
    scd_netbox.netbox.ipam.ip_addresses.filter = mocker.MagicMock(return_value=[deepcopy(fake_address_physical)])
    scd_netbox.netbox.dcim.devices.get = mocker.MagicMock(return_value=deepcopy(FAKE.DEVICE_PHYSICAL))
    assert FAKE.DEVICE_PHYSICAL == FAKE.DEVICE_PHYSICAL
    assert FAKE.DEVICE_PHYSICAL == scd_netbox.get_device_by_hostname('foo.example.org')
    scd_netbox.netbox.ipam.ip_addresses.filter.assert_called_with(dns_name='foo.example.org', family=4)
    scd_netbox.netbox.dcim.devices.get.assert_called_with(277636)

    # Test a virtual interface
    scd_netbox.netbox.ipam.ip_addresses.filter = mocker.MagicMock(return_value=[deepcopy(fake_address_virtual)])
    scd_netbox.netbox.virtualization.virtual_machines.get = mocker.MagicMock(return_value=deepcopy(FAKE.DEVICE_VIRTUAL))
    assert FAKE.DEVICE_VIRTUAL == scd_netbox.get_device_by_hostname('bar.example.org')
    scd_netbox.netbox.ipam.ip_addresses.filter.assert_called_with(dns_name='bar.example.org', family=4)
    scd_netbox.netbox.virtualization.virtual_machines.get.assert_called_with(6465)

    # Should log an error and exit if an unknown type is found
    scd_netbox = SCDNetbox()
    scd_netbox.netbox.ipam.ip_addresses = SimpleNamespace()
    scd_netbox.netbox.ipam.ip_addresses.filter = mocker.MagicMock(return_value=[fake_address_garbage])
    mocked_error = mocker.patch.object(logging, 'error')
    with pytest.raises(SystemExit):
        scd_netbox.get_device_by_hostname('unknowntype.example.org')
    mocked_error.assert_called()

    # Should log an error and exit if nothing is found
    scd_netbox = SCDNetbox()
    scd_netbox.netbox.ipam.ip_addresses = SimpleNamespace()
    scd_netbox.netbox.ipam.ip_addresses.filter = mocker.MagicMock(return_value=None)
    mocked_error = mocker.patch.object(logging, 'error')
    with pytest.raises(SystemExit):
        scd_netbox.get_device_by_hostname('doesnotexist.example.org')
    mocked_error.assert_called()

    # Should log an error and exit if multiple addresses are found
    scd_netbox = SCDNetbox()
    scd_netbox.netbox.ipam.ip_addresses = SimpleNamespace()
    scd_netbox.netbox.ipam.ip_addresses.filter = mocker.MagicMock(return_value=[
        fake_address_physical,
        fake_address_virtual,
    ])
    mocked_error = mocker.patch.object(logging, 'error')
    with pytest.raises(SystemExit):
        scd_netbox.get_device_by_hostname('multihost.example.org')
    mocked_error.assert_called()


def test_get_rack_from_device(mocker):
    """
    Test that get_rack_from_device returns a rack or exits with an error
    """
    scd_netbox = SCDNetbox()

    fake_rack = SimpleNamespace(
        facility_id='152',
    )

    scd_netbox.netbox.dcim.racks = SimpleNamespace()
    scd_netbox.netbox.dcim.racks.get = mocker.MagicMock(return_value=deepcopy(fake_rack))
    assert fake_rack == scd_netbox.get_rack_from_device(deepcopy(FAKE.DEVICE_PHYSICAL))
    scd_netbox.netbox.dcim.racks.get.assert_called_with(368)

    # Should log an error and exit if nothing is found
    scd_netbox.netbox.dcim.racks.get = mocker.MagicMock(return_value=deepcopy(None))
    mocked_error = mocker.patch.object(logging, 'error')
    with pytest.raises(SystemExit):
        scd_netbox.get_rack_from_device(FAKE.DEVICE_PHYSICAL)
    mocked_error.assert_called()


def test_get_interfaces_from_device(mocker):
    """ Test get_interfaces_from_device """
    test_obj = SCDNetbox()

    # Test physical interfaces
    # The last one has no MAC address and should not be returned, but a warning should be issued
    test_obj.netbox.dcim.interfaces = SimpleNamespace()
    test_obj.netbox.dcim.interfaces.filter = mocker.MagicMock(return_value=deepcopy(FAKE.INTERFACES_PHYSICAL))
    mocked_warning = mocker.patch.object(logging, 'warning')
    assert FAKE.INTERFACES_PHYSICAL[:-1] == test_obj.get_interfaces_from_device(deepcopy(FAKE.DEVICE_PHYSICAL))
    mocked_warning.assert_called()

    # Test virtual interfaces
    test_obj.netbox.virtualization.interfaces = SimpleNamespace()
    test_obj.netbox.virtualization.interfaces.filter = mocker.MagicMock(return_value=deepcopy(FAKE.INTERFACES_VIRTUAL))
    assert FAKE.INTERFACES_VIRTUAL == test_obj.get_interfaces_from_device(deepcopy(FAKE.DEVICE_VIRTUAL))

    # Should log an error and exit if an unknown type is passed
    mocked_error = mocker.patch.object(logging, 'error')
    with pytest.raises(SystemExit):
        test_obj.get_interfaces_from_device(SimpleNamespace())
    mocked_error.assert_called()


def test_get_addresses_from_interface(mocker):
    """ Test get_addresses_from_interface """
    scd_netbox = SCDNetbox()

    # Should filter by interface_id if physical
    scd_netbox.netbox.ipam.ip_addresses = SimpleNamespace()
    scd_netbox.netbox.ipam.ip_addresses.filter = mocker.MagicMock(return_value=deepcopy(FAKE.ADDRESSES_IPV4))
    assert FAKE.ADDRESSES_IPV4 == scd_netbox.get_addresses_from_interface(FAKE.INTERFACES_PHYSICAL[0])
    scd_netbox.netbox.ipam.ip_addresses.filter.assert_called_with(interface_id=34623)

    # Should filter by vminterface_id if virtual
    scd_netbox.netbox.ipam.ip_addresses = SimpleNamespace()
    scd_netbox.netbox.ipam.ip_addresses.filter = mocker.MagicMock(return_value=[])
    assert len(scd_netbox.get_addresses_from_interface(FAKE.INTERFACES_VIRTUAL[0])) == 0
    scd_netbox.netbox.ipam.ip_addresses.filter.assert_called_with(vminterface_id=3768)

    # Should raise a warning and return an empty list if an unknown type is passed
    scd_netbox.netbox.ipam.ip_addresses = SimpleNamespace()
    mocked_warning = mocker.patch.object(logging, 'warning')
    assert len(scd_netbox.get_addresses_from_interface(SimpleNamespace(count_ipaddresses=42))) == 0
    mocked_warning.assert_called()

    # Should raise a warning and return an empty list if only an IPv6 address is found
    scd_netbox.netbox.ipam.ip_addresses = SimpleNamespace()
    scd_netbox.netbox.ipam.ip_addresses.filter = mocker.MagicMock(return_value=deepcopy(FAKE.ADDRESSES_IPV6))
    mocked_warning = mocker.patch.object(logging, 'warning')
    assert len(scd_netbox.get_addresses_from_interface(SimpleNamespace(count_ipaddresses=2112))) == 0
    mocked_warning.assert_called()
