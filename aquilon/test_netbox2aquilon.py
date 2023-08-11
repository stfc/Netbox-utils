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

    add_interface_base_cmd = ['add_interface', '--machine', 'system7592']

    add_bmc0 = add_interface_base_cmd + ['--mac', 'A1:B2:C3:D4:E5:3F', '--interface', 'bmc0', '--iftype', 'management']
    add_eth0 = add_interface_base_cmd + ['--mac', 'A1:B2:C3:D4:E5:DA', '--interface', 'eth0']
    add_eth1 = add_interface_base_cmd + ['--mac', 'A1:B2:C3:D4:E5:DB', '--interface', 'eth1']

    update_eth0 = ['update_interface', '--machine', 'system7592', '--interface', 'eth0', '--boot']

    cmds = test_obj._netbox_copy_interfaces(fake_device)

    assert len(cmds) == 4
    assert add_bmc0 in cmds
    assert add_eth0 in cmds
    assert add_eth1 in cmds
    assert update_eth0 in cmds
    # eth0 must be added before being updated
    assert cmds.index(add_eth0) < cmds.index(update_eth0)


    # Virtual machine with two interfaces
    fake_device = SimpleNamespace(
        aq_machine_name='system6690',
    )
    test_obj.get_interfaces_from_device = mocker.MagicMock(return_value=deepcopy(FAKE.INTERFACES_VIRTUAL))
    add_eth0 = ['add_interface', '--machine', 'system6690', '--mac', 'A1:B2:C3:D4:E5:1B', '--interface', 'eth0']
    add_eth1 = ['add_interface', '--machine', 'system6690', '--mac', 'A1:B2:C3:D4:E5:99', '--interface', 'eth1']
    update_eth0 = ['update_interface', '--machine', 'system6690', '--interface', 'eth0', '--boot']

    cmds = test_obj._netbox_copy_interfaces(fake_device)

    assert len(cmds) == 3
    assert add_eth0 in cmds
    assert add_eth1 in cmds
    assert update_eth0 in cmds
    # eth0 must be added before being updated
    assert cmds.index(add_eth0) < cmds.index(update_eth0)

def test__netbox_copy_addresses(mocker):
    test_obj = Netbox2Aquilon()

    fake_device = FAKE.DEVICE_PHYSICAL
    fake_device.aq_machine_name = 'system7592'

    # No addresses on an interface
    test_obj.get_interfaces_from_device = mocker.MagicMock(return_value=[deepcopy(FAKE.INTERFACES_PHYSICAL)[1]])
    test_obj.get_addresses_from_interface = mocker.MagicMock(return_value=[])
    assert not test_obj._netbox_copy_addresses(fake_device)

    # Addresses on an interface
    test_obj.get_interfaces_from_device = mocker.MagicMock(return_value=[deepcopy(FAKE.INTERFACES_PHYSICAL[1])])
    test_obj.get_addresses_from_interface = mocker.MagicMock(return_value=deepcopy(FAKE.ADDRESSES_IPV4))
    assert test_obj._netbox_copy_addresses(fake_device) == [
        [
            'add_interface_address', '--machine',
            'system7592', '--interface',
            'eth0', '--ip', '192.168.180.13',
            '--fqdn', 'aquilon.example.org',
        ],
    ]


def test__netbox_get_personality(mocker):
    test_obj = Netbox2Aquilon()

    fake_devices = [
        # Tuple containing the device object and the name of role attribute in this device type
        (deepcopy(FAKE.DEVICE_PHYSICAL), 'device_role'),
        (deepcopy(FAKE.DEVICE_VIRTUAL), 'role'),
    ]

    # Test with devices that present as physical and virtual
    # Currently this only changes the name of the attribute containing the role
    for dev, role_attr in fake_devices:
        if hasattr(dev, 'role'):
            del dev.role
        if hasattr(dev, 'role'):
            del dev.device_role

        # Test without and with a personality specified
        # If once is specified it should always be returned as long as aquilon can find it
        for opt in (None, 'dave'):
            # All combinations of role and tenant, pretending that aquilon will accept any personality
            # Should return 'inventory' unless both role and tenant are set
            test_obj._call_aq = mocker.MagicMock(return_value=0)

            setattr(dev, role_attr, None)
            dev.tenant = None
            assert test_obj._netbox_get_personality(dev, 'fake_archetype', opt) == opt if opt else 'inventory'

            setattr(dev, role_attr, SimpleNamespace(slug='roland'))
            dev.tenant = None
            assert test_obj._netbox_get_personality(dev, 'fake_archetype', opt) == opt if opt else 'inventory'

            setattr(dev, role_attr, None)
            dev.tenant = SimpleNamespace(slug='tennant')
            assert test_obj._netbox_get_personality(dev, 'fake_archetype', opt) == opt if opt else 'inventory'

            setattr(dev, role_attr, SimpleNamespace(slug='roland'))
            dev.tenant = SimpleNamespace(slug='tennant')
            assert test_obj._netbox_get_personality(dev, 'fake_archetype', opt) == opt if opt else 'roland-tennant'


            # All combinations of role and tenant, pretending that aquilon will not accept anything
            # Should always return 'inventory'
            test_obj._call_aq = mocker.MagicMock(return_value=1)

            setattr(dev, role_attr, None)
            dev.tenant = None
            assert test_obj._netbox_get_personality(dev, 'fake_archetype', opt) == 'inventory'

            setattr(dev, role_attr, SimpleNamespace(slug='roland'))
            dev.tenant = None
            assert test_obj._netbox_get_personality(dev, 'fake_archetype', opt) == 'inventory'

            setattr(dev, role_attr, None)
            dev.tenant = SimpleNamespace(slug='tennant')
            assert test_obj._netbox_get_personality(dev, 'fake_archetype', opt) == 'inventory'

            setattr(dev, role_attr, SimpleNamespace(slug='roland'))
            dev.tenant = SimpleNamespace(slug='tennant')
            assert test_obj._netbox_get_personality(dev, 'fake_archetype', opt) == 'inventory'


def test__undo_cmds():
    test_obj = Netbox2Aquilon()

    cmds_forward = [
        [
            'add_machine',
            '--machine', 'system6690',
            '--vendor', 'virtual',
            '--model', 'foo-bar',
            '--cluster', 'vmware-foo',
            '--cpuname', 'xeon_e5_2650v4',
            '--cpuspeed', '2200',
            '--cpucount', '2',
            '--memory', '38400',
        ],
        [
            'add_disk',
            '--machine', 'system6690',
            '--disk', 'sda',
            '--controller', 'sata',
            '--size', '40',
            '--boot',
        ],
        [
            'add_interface',
            '--machine', 'system6690',
            '--mac', 'A1:B2:C3:D4:E5:1B',
            '--interface', 'eth0',
        ],
        [
            'add_interface',
            '--machine', 'system6690',
            '--mac', 'A1:B2:C3:D4:E5:99',
            '--interface', 'eth1',
        ],
        [
            'update_interface',
            '--machine', 'system6690',
            '--interface', 'eth0',
            '--boot',
        ],
        [
            'add_host',
            '--hostname', 'www.example.org',
            '--machine', 'system6690',
            '--archetype', 'dave',
            '--ip', '192.168.180.221',
            '--personality', 'inventory',
            '--sandbox', 'bob/test',
            '--osname', 'rocky',
            '--osversion', '8x-x86_64',
        ],
        [
            'add_interface_address',
            '--machine', 'system6690',
            '--interface', 'eth0',
            '--ip', '192.168.180.53',
            '--fqdn', 'overwatch.example.org',
        ],
    ]

    cmds_reverse = [
        [
            'del_interface_address',
            '--machine', 'system6690',
            '--interface', 'eth0',
            '--ip', '192.168.180.53',
        ],
        [
            'del_host',
            '--hostname', 'www.example.org',
        ],
        [
            'del_interface',
            '--machine', 'system6690',
            '--interface', 'eth1',
        ],
        [
            'del_interface',
            '--machine', 'system6690',
            '--interface', 'eth0',
        ],
        [
            'del_disk',
            '--machine', 'system6690',
            '--disk', 'sda',
        ],
        [
            'del_machine',
            '--machine', 'system6690',
        ],
    ]

    assert test_obj._undo_cmds(cmds_forward) == cmds_reverse
