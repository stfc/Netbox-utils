from data_uploader.netbox_api.netbox_connection import NetboxApi


class NetboxBase:
    def __init__(self, url, token, cert):
        self.url = url
        self.token = token
        self.cert = cert
        self._netbox_api = NetboxApi.api_object(url, token, cert)
