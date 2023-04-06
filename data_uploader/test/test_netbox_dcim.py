import unittest
from unittest.mock import NonCallableMock, MagicMock, patch
from data_uploader.netbox_api.netbox_dcim import NetboxDcim
from nose.tools import assert_true, assert_is_not_none, raises
from data_uploader.exceptions.mac_address_collision_error import MacAddressCollisionError
from pynetbox.core.response import Record

# WIP
class NetboxDcimTests(unittest.TestCase):

    """
    Runs tests to ensure we are interacting with the NetBox
    API for dcim objects in the expected way
    """

    def test_get_device_response(self):
        """
        Test that we can interact with netbox and get a response
        """
        self._netbox_api = MagicMock()
        mock_device_name = NonCallableMock()
        response = NetboxDcim.get_device(self._netbox_api, hostname=mock_device_name)
        assert_true(response.ok)
        assert_is_not_none(response)

    def test_get_device_none_found(self):
        """
        Test that get_device does return None if a device is not in Netbox
        """
        pass

    def test_get_device_type(self):
        """
        Test that we can interact with NetBox to get a device type and
        get a response back
        :return:
        """
        self._netbox_api = MagicMock()
        mock_model = NonCallableMock()
        response = NetboxDcim.get_device_types(model=mock_model)
        assert_true(response.ok)
        assert_is_not_none(response)
        # TO DO assert a value is actually returned by get device type

    def test_get_device_type_none_found(self):
        """
        Test None is returned if device type not in Netbox
        """
        pass

    def test_get_interface(self):
        """
        Test get_interface method
        """
        self._netbox_api = MagicMock()
        mock_interface = NonCallableMock()
        mock_hostname = NonCallableMock()

        response = NetboxDcim.get_interface(self, interface_name=mock_interface, hostname=mock_hostname)
        assert_true(response.ok)
        assert_is_not_none(response)

    def test_find_mac_addr(self):
        """
        Test checking for a mac address in Netbox
        """
        self._netbox_api = MagicMock()
        mock_mac_addr = NonCallableMock()

        response = NetboxDcim.find_mac_addr(self, mac_address=mock_mac_addr)
        assert_true(response)

    def test_no_mac_addr_found(self):
        """
        Test False is returned when a mac address is missing in Netbox
        """
        # WIP
        pass

    def test_create_device(self):
        """
        Test creating a device
        """
        # WIP
        self._netbox_api = MagicMock()
        mock_hostname = NonCallableMock()
        mock_site = NonCallableMock()
        mock_location = NonCallableMock()
        mock_tenant = NonCallableMock()
        mock_manufacturer = NonCallableMock()
        mock_rack = NonCallableMock()
        mock_rack_position = NonCallableMock()
        mock_device_type = NonCallableMock()
        mock_serial_no = NonCallableMock()

        device = NetboxDcim.create_device(self, hostname=mock_hostname, site=mock_site, location=mock_location, tenant=mock_tenant, manufacturer=mock_manufacturer,
                                          rack=mock_rack, rack_position=mock_rack_position, device_type=mock_device_type, serial_no=mock_serial_no)

        pass

    def test_create_device_type(self):
        """
        Test creating a device type
        """
        # WIP
        self._netbox_api = MagicMock()
        mock_model = NonCallableMock()
        mock_manufacturer = NonCallableMock()
        mock_slug = NonCallableMock()
        mock_unit_height = NonCallableMock()

        device_type = NetboxDcim.create_device_type(self, model=mock_model, manufacturer=mock_manufacturer, slug=mock_slug, unit_height=mock_unit_height)
        pass

    # currently failing test as raising MAC address error
    def test_create_interface(self):
        """
        Test interface creation
        """
        # WIP
        self._netbox_api = MagicMock()
        mock_interface = NonCallableMock()
        mock_hostname = NonCallableMock()
        mock_interface_type = NonCallableMock()
        mock_description = NonCallableMock()
        mock_mac_addr = NonCallableMock()
        mock_mac_addr_match = NetboxDcim.find_mac_addr(self._netbox_api, mac_address=mock_mac_addr)

        interface = NetboxDcim.create_interface(self._netbox_api, interface_name=mock_interface, hostname=mock_hostname, interface_type=mock_interface_type,
                                                description=mock_description, mac_address=mock_mac_addr)

        # assert value is returned

    #@patch(NetboxDcim.find_mac_addr)
    #@raises(MacAddressCollisionError)
    def test_mac_address_collision(self):
        """
        Test if interface creation is attempted
        and mac address already exists then an error
        is raised
        """
        # WIP
        self._netbox_api = MagicMock()
        mac_addr_match = False

        pass