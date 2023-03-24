from data_uploader.netbox_api.netbox_dcim import NetboxDcim
from data_uploader.netbox_api.netbox_connection import NetboxApi
import pynetbox

class NetboxIpam:
    def __init__(self, url, token, cert):
        self.url = url
        self.token = token
        self. cert = cert
        self._netbox_api = NetboxApi.api_object(url, token, cert)

    def search_mac_address(self, mac_addr: str):
        """
        Search Netbox for a mac address assigned to any interface
        This will call a method from NetBox Dcim to do this
        :return: Record object with interface the mac address is associated with or None if not found
        """
        netbox = self._netbox_api
        interface = netbox.dcim.interfaces.get(mac_address=mac_addr)

        return interface

    def get_ip_address(self, ip_addr: str):
        """
        Search netbox for an IP Address
        :param ip_addr: IP address to search for in Netbox
        :return: Record object with IP Address or None if not found
        """
        netbox = self._netbox_api
        return netbox.ipam.ip_addresses.get(address=ip_addr)

    def create_ip_address(self, hostname: str, interface:str, ip_address: str, tenant: str):
        """
        Create a new IP address in Netbox
        :param hostname: Name of device in Netbox (must be present in Netbox)
        :param interface: Interface attached to device (must be present in Netbox)
        :param ip_address: IP address to create
        :param tenant:  Tenant IP address belongs to (must be present in Netbox)
        """

        interface = NetboxDcim.get_interface(name=interface, device=hostname)
        netbox_ip = netbox.ipam.ip_addresses.create(
            address="ip-address",
            tenant=netbox.tenancy.tenants.get(name='tenant-name').id,
            tags=[{'name': 'Tag 1'}],
        )
        # assign IP Address to device's network interface
        netbox_ip.assigned_object = interface
        netbox_ip.assigned_object_id = interface.id
        netbox_ip.assigned_object_type = 'dcim.interface'
        # save changes to IP record in Netbox
        netbox_ip.save()
