from data_uploader.exceptions.missing_mandatory_param_error import MissingMandatoryParamError
import requests
from pynetbox import api


class NetboxApi:
    """
    Wraps a netbox connection as a context manager

    """
    def __init__(self):
        pass

    @staticmethod
    def api_object(netbox_url: str, token: str, cert=None):
        if not netbox_url:
            raise MissingMandatoryParamError(
                "NetBox URL is required but not provided."
            )
        if not token:
            raise MissingMandatoryParamError(
                "A token is required but not provided."
            )
        session = requests.Session()
        session.verify = cert if cert else False

        connection = api(url=netbox_url, token=token)
        connection.http_session = session

        return connection
