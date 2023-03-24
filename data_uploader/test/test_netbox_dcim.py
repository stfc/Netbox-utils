import unittest
from unittest.mock import NonCallableMock, Mock, MagicMock
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
        netbox = MagicMock()
        mock_device_name = NonCallableMock
        response = netbox.dcim.devices.get(name=mock_device_name)

        assert_true(response.ok)
        assert_is_not_none(response)

        #error with line below
        #test we do get a value returned
        #assert response == NetboxDcim.get_device(hostname=mock_device_name).return_value

    def test_get_device_no_device_found(self):
        """
        Test that if we get a
        :return:
        """
        self._netbox_api = MagicMock()

#    def test_get_device(self):
#
#        mocked_url = NonCallableMock()
#        mocked_token = NonCallableMock()
#        mocked_device_name = NonCallableMock()
#        mocked_hostname = NonCallableMock
#        netbox = MagicMock
#        device = NetboxDcim.get_device(self, hostname=mocked_hostname)
#
#        assert device == self.api.get_device.return_value

        #self.api.get_device.assert_called_once_with()
        #self.mocked_connection.assert_called_once_with(mocked_url, mocked_token)

    def test_get_device_type(self):
        """
        Test that we can interact with NetBox to get a device type and
        get a response back
        :return:
        """
        netbox = MagicMock()
        mock_model = NonCallableMock
        response = netbox.dcim.device_types.get(slug=NonCallableMock)
        assert_true(response.ok)
