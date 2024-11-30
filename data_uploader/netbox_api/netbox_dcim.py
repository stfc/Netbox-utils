from typing import Union
from data_uploader.exceptions.mac_address_collision_error import MacAddressCollisionError
from data_uploader.netbox_api.netbox_base import NetboxBase
from pynetbox.core.response import Record


class NetboxDcim(NetboxBase):
    """
    Class for retrieving or creating DCIM objects in Netbox
    """
    def __init__(self, url, token, cert):
        super().__init__(url, token, cert)

    def get_device(self, hostname: str) -> Union[Record, None]:
        """
        Search for the name of a device (server) in Netbox by its name
        :param hostname: name of the server to search for in Netbox
        :return: dict of record in netbox or None if not found
        """
        self._netbox_api.dcim.devices.get(name=hostname)
        return self._netbox_api.dcim.devices.get(name=hostname)

    def get_device_types(self, model: str) -> Union[Record, None]:
        """
        Get device model type from netbox
        :param model: model type to search for in netbox
        :return: dict of record in netbox or None if not found
        """

        return self._netbox_api.dcim.device_types.get(slug=model)

    def get_interface(self, interface_name: str, hostname: str) -> Union[Record, None]:
        """
        Get an interface from Netbox
        :param interface_name: Name of interface to search for
        :param hostname: Name of device the interface is attached to
        """
        return self._netbox_api.dcim.interfaces.get(name=interface_name, device=hostname)

    def find_mac_addr(self, mac_address: str) -> bool:
        """
        Checks whether there is an interface in Netbox that already uses a specific mac address
        :param mac_address: mac address to search Netbox for
        :returns: Boolean indicating whether an interface with that address exists (True) or not (False)
        """
        check = self._netbox_api.interface.get(mac_address=mac_address)
        return True if check else False

    def create_device(self, hostname: str, site: str, location: str, tenant: str, manufacturer: str,
                      rack: str, rack_position: int, device_type: str, serial_no: str) -> Record:
        """
        Create a new device in NetBox.

        :param hostname: Name of device
        :param site: Building and Room the device is located in
        :param location: Row the device is in
        :param tenant: Tenant for the device
        :param manufacturer: Device manufacturer
        :param rack: Rack the device is in
        :param rack_position: Rack position (Optional)
        :param device_type: Device type
        :param serial_no: serial number (optional)

        :return: Netbox Record object
        """
        netbox = self._netbox_api
        netbox_device = netbox.dcim.devices.create(
            name=hostname,
            site=netbox.dcim.devices.get(name=site).id,
            location=netbox.dcim.locations.get(name=location).id,
            tenant=netbox.tenancy.tenants.get(name=tenant).id,
            manufacturer=netbox.dcim.manufacturers.get(name=manufacturer).id,  # optional field
            rack=netbox.dcim.racks.get(name=rack).id,
            postion=rack_position,  # optional field - omit this field if the device is unracked
            device_type=netbox.dcim.device_types.get(slug=device_type).id,
            serial=serial_no,  # optional field
            #tags=[{"name": "Tag 1"}, {"name": "Tag 2"}]  # optional field
        )
        return netbox_device

    def create_device_type(self, model: str, manufacturer: str, slug: str, unit_height: int) -> Record:
        """
        Create a new device type in NetBox
        :param model: Name of device type
        :param manufacturer: name of manufacturer
        :param slug: slug of model name
        :param unit_height: height of devices of this type

        :return: Netbox record of new device type
        """
        netbox = self._netbox_api
        new_device_type = netbox.dcim.device_types.create(
            manufacturer=netbox.dcim.manufacturers.get(name=manufacturer).id,
            model=model,
            slug=slug,
            u_height=unit_height,
        #    custom_fields={'cf_1': 'Custom data 1'}  # optional field
        )
        return new_device_type

    def create_interface(self, interface_name: str, hostname: str, interface_type: str, description: str,
                         mac_address: str) -> Record:
        """
        Create an interface for a device already in NetBox
        :param interface_name: name of interface
        :param hostname: name of device the interface is attached to
        :param interface_type: interface type
        :param description: description
        :param mac_address: mac_address
        :return: netbox_interface: Record object with details of newly created netbox interface
        """
        # verify whether the mac address already exists in Netbox on a specific interface
        mac_addr_match = NetboxDcim.find_mac_addr(self, mac_address)

        if mac_addr_match:
            raise MacAddressCollisionError(
                "MAC Address already exists in Netbox"
            )

        netbox = self._netbox_api

        netbox_interface = netbox.dcim.interfaces.create(
            name=interface_name,
            device=netbox.dcim.devices.get(name=hostname).id,
            type=interface_type,
            description=description,
            mac_address=mac_address,
        #   tags = [{'name': 'Tag 1'}]
        )
        return netbox_interface
