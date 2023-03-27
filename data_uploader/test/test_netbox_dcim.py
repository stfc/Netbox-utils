import unittest
from unittest.mock import NonCallableMock, MagicMock
from data_uploader.netbox_api.netbox_dcim import NetboxDcim
from data_uploader.netbox_api.netbox_connection import NetboxApi
from nose.tools import assert_true, assert_is_not_none


class NetboxDcimTests(unittest.TestCase):
    """
    Runs tests to ensure we are interacting with the NetBox
    API for dcim objects in the expected way
    """

    def test_get_device_response(self):
        """
        Test that we can interact with netbox and get a response
        :return:
        """
        self._netbox_api = MagicMock()
        mock_device_name = NonCallableMock()
        response = self._netbox_api.dcim.devices.get(name=mock_device_name)

        assert_true(response.ok)
        assert_is_not_none(response)

        # assert that a value is returned
       # assert NetboxDcim.get_device(hostname=mock_device_name).return_value == response

    #def test_get_device_no_device_found(self):
    #    """
    #    Test that if we get a
    #    :return:
    #    """
    #    self._netbox_api = MagicMock()

    def test_get_device_type(self):
        """
        Test that we can interact with NetBox to get a device type and
        get a response back
        :return:
        """
        self._netbox_api = MagicMock()
        mock_model = NonCallableMock()
        response = self._netbox_api.dcim.device_types.get(slug=mock_model)
        assert_true(response.ok)
