import unittest
from unittest.mock import NonCallableMock, patch
from nose.tools import raises
from data_uploader.exceptions.missing_mandatory_param_error import MissingMandatoryParamError
from data_uploader.netbox_api.netbox_connection import NetboxApi


class NetboxApiTests(unittest.TestCase):
    @staticmethod
    @patch('data_uploader.netbox_api.netbox_connection.api')
    def test_api_object_create(mock_api):
        """
        Tests that we do get an API object an
        """
        mock_url = "example.com"
        mock_token = NonCallableMock()
        mock_cert = NonCallableMock()

        api = NetboxApi.api_object(mock_url, mock_token, mock_cert)
        assert mock_api.return_value == api

    @staticmethod
    @patch('data_uploader.netbox_api.netbox_connection.api')
    def test_api_no_cert(mock_api):
        """
        Test that an api object is created even when we don't have a path for a certificate
        """
        mock_url = "example.com"
        mock_token = NonCallableMock()
        mock_cert = None

        api = NetboxApi.api_object(mock_url, mock_token, mock_cert)
        assert mock_api.return_value == api

    @raises(MissingMandatoryParamError)
    def test_api_throws_for_no_url(self):
        """
        Tests a None type will throw error if used as url
        """
        missing_url = None
        mock_token = NonCallableMock()
        mock_cert = NonCallableMock()
        api = NetboxApi.api_object(missing_url, mock_token, mock_cert)
        api.assertRaises(MissingMandatoryParamError)

    @raises(MissingMandatoryParamError)
    def test_api_throws_for_no_token(self):
        """
        Tests a None type will throw if used as token
        """
        mock_url = NonCallableMock()
        missing_token = None
        mock_cert = NonCallableMock()
        NetboxApi.api_object(mock_url, missing_token, mock_cert)
        self.assertRaises(MissingMandatoryParamError)
