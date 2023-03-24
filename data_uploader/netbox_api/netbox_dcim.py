from data_uploader.netbox_api.netbox_connection import NetboxApi


class NetboxDcim():
    def __init__(self, url, token, cert=None):
        self.url = url
        self.token = token
        self. cert = cert
            #'= NetboxApi.api_object(url, token, cert)

        self._netbox_api = NetboxApi.api_object(url, token, cert)

    def get_device(self, hostname: str):
        """
        Search for the name of a device (server) in Netbox by its name
        :param netbox_url: Netbox url
        :param token: Token to connect to url
        :param cert_path:  path to certificate (required for Production)
        :param hostname: name of the server to search for in Netbox
        :return: dict of record in netbox or None if not found
        """
        netbox = self._netbox_api

        return netbox.dcim.devices.get(name=hostname)

    def get_device_types(self, model):
        """
        Get device model type from netbox
        :param model: model type to search for in netbox
        :return: dict of record in netbox or None if not found
        """
        netbox = self._netbox_api

        return netbox.dcim.device_types.get(slug=model)

    def get_interface(self, interface_name, hostname):
        """
        Get an interface from Netbox
        :param interface_name: Name of interface to search for
        :param hostname: Name of device the interface is attached to
        """
        netbox = self._netbox_api
        return netbox.dcim.interfaces.get(name=interface_name, device=hostname)


    def create_device(self, **kwargs):
        """
        Create a new device in NetBox
        :param kwargs:
        :return: Netbox Record object
        """
        netbox = self._netbox_api

        #netbox_device = netbox.dcim.devices.create(
        #    name=hostname,
        #    site=netbox.dcim.devices.get(name=site).id,
        #    location=netbox.dcim.locations.get(name=location).id,
        #    tenant=netbox.tenancy.tenants.get(name=tenant).id,
        #    manufacturer=netbox.dcim.manufacturers.get(name=manufacturer).id,  # optional field
        #    rack=netbox.dcim.racks.get(name=rack).id,
        #    postion=rack_position,  # optional field - omit this field if the device is unracked
        #    device_type=netbox.dcim.device_types.get(slug=device_type).id,
        #    serial=serial_no,  # optional field
        #    custom_fields={'cf_1': 'Custom data 1'},  # optional field
        #    tags=[{"name": "Tag 1"}, {"name": "Tag 2"}]  # optional field
        #)
        pass

    def create_device_type(self, **kwargs):
        """
        Create a new device type in NetBox
        :return:
        """
        netbox = self._netbox_api

        #new_device_type = netbox.dcim.device_types.create(
        #    manufacturer=netbox.dcim.manufacturers.get(name="manufacturer-name").id,
        #    model="device-type-name",
        #    slug="device-type-slug",
        #    subdevice_role='child or parent',
            # optional field - required if creating a device type to be used for a child device
        #    u_height=unit_height,
            # Can only equal 0 if the device type is for a child device - requires subdevice_role='child' if that is the case
        #    custom_fields={'cf_1': 'Custom data 1'}  # optional field
        #)
        pass


    def create_interface(self, **kwargs):
        """
        Create an interface for a device already in NetBox
        :param kwargs:
        :return:
        """
        netbox = self._netbox_api
        #netbox_interface = netbox.dcim.interfaces.create(
        #    name="interface-name",
        #    device=netbox.dcim.devices.get(name=hostname)]).id,
        #   type = "interface-type",
        #   description = "description",
        #   mac_address = "mac-address",
        #   tags = [{'name': 'Tag 1'}]
        #)
        pass