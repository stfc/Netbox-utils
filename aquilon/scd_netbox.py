"""
    Library of common functionality used for interacting with SCD's NetBox instance
"""

import configparser
import logging
import os.path
import sys
import requests
import pynetbox


class SCDNetbox():
    """
        This class is intended to either used directly, or subclassed by other tools to add extra functionality.
    """
    def __init__(self, additonal_config_name=None):
        """ Connect to NetBox and set up session """
        netbox_session = requests.Session()

        self.config = configparser.ConfigParser()
        self.config['netbox'] = {
            'url': 'https://netbox.example.org/',
            'cert_path': '',
            'token': 'TOKEN',
        }
        self.config['aquilon'] = {
            'archetype': 'ral-tier1',
            'osname': 'rocky',
            'osversion': '8x-x86_64',
            'cli_path': '/opt/aquilon/bin/aq.py',
            'domain': 'staging',
            'cpuname': 'xeon_e5_2650v4',
            'cpuspeed': '2200',
        }
        self.config.read([
            '/var/quattor/etc/scd_netbox.cfg',
            os.path.expanduser('~/.scd_netbox.cfg'),
        ])
        if additonal_config_name:
            self.config.read([
                f'/var/quattor/etc/{additonal_config_name}.cfg',
                os.path.expanduser(f'~/.{additonal_config_name}.cfg'),
            ])

        if self.config['netbox']['cert_path']:
            if self.config['netbox']['cert_path'].lower() == 'false':
                netbox_session.verify = False
            else:
                netbox_session.verify = self.config['netbox']['cert_path']

        self.netbox = pynetbox.api(self.config['netbox']['url'], token=self.config['netbox']['token'])
        self.netbox.http_session = netbox_session

    def get_device_by_magdb_id(self, magdb_id):
        """ Get a single device from NetBox based on MagDB system ID """
        device = self.netbox.dcim.devices.get(cf_magdb_system_id=magdb_id)

        if device is None:
            logging.error("Device not found in NetBox")
            sys.exit(1)

        logging.debug("Got device %s for MagDB ID %s", device, magdb_id)
        return device

    def get_device_by_name(self, name):
        """ Get a single device from NetBox based on device name """
        device = self.netbox.dcim.devices.get(name=name)

        if device is None:
            logging.error("Device not found in NetBox")
            sys.exit(1)

        logging.debug("Got device %s for name %s", device, name)
        return device

    def get_device_by_hostname(self, hostname):
        """ Get a single device from NetBox based on fully qualified domain name """
        ip_address = self.netbox.ipam.ip_addresses.get(dns_name=hostname)
        if ip_address is None:
            logging.error("Hostname not found in NetBox")
            sys.exit(1)

        logging.debug("Got IP %s for hostname %s", ip_address, hostname)

        # The ip_address is assigned to an object, which is what we are after,
        # unfortunately the property will return a pynetbox.core.response.Record object,
        # so we need to use the id to obtain the "real" object and preserve the type.
        if ip_address.assigned_object_type == 'dcim.interface':
            logging.debug("IP %s is assigned to a physical interface", ip_address)
            device = self.netbox.dcim.devices.get(ip_address.assigned_object.device.id)
        elif ip_address.assigned_object_type == 'virtualization.vminterface':
            logging.debug("IP %s is assigned to a virtual machine interface", ip_address)
            device = self.netbox.virtualization.virtual_machines.get(ip_address.assigned_object.virtual_machine.id)
        else:
            logging.error("Unknown assigned_object_type %s for IP %s", ip_address.assigned_object_type, ip_address)
            sys.exit(1)

        if device is None:
            logging.error("Device not found in NetBox")
            sys.exit(1)

        logging.debug("Got device %s for hostname %s", device, hostname)
        return device

    def get_rack_from_device(self, device):
        """ check if host is in rack - query netbox for rack """
        rack = self.netbox.dcim.racks.get(device.rack.id)

        if rack is None:
            logging.error("host not in rack?")
            sys.exit(1)

        # check facility_id is present
        if rack.facility_id is None:
            logging.error("no facility ID found for rack")
            sys.exit(1)

        return rack

    def get_interfaces_from_device(self, device):
        """
        The next step is to add interfaces to the machine in Aquilon
        We need to use 'filter' to retrieve the interface id for all interfaces
        This will assume that the device name IS UNIQUE
        """
        if isinstance(device, pynetbox.models.dcim.Devices):
            filter_interfaces = self.netbox.dcim.interfaces.filter(device=device.name)
        elif isinstance(device, pynetbox.models.virtualization.VirtualMachines):
            filter_interfaces = self.netbox.virtualization.interfaces.filter(virtual_machine=device.name)
        else:
            logging.error('Unsupported device type for interfaces "%s"', type(device))
            sys.exit(1)

        if len(filter_interfaces) == 0:
            logging.error("No interfaces found")
            sys.exit(1)

        interfaces = []
        unusedintf = 0
        for interface in filter_interfaces:
            if interface.mac_address:
                interfaces.append(interface)
            else:
                unusedintf += 1

        if unusedintf:
            logging.warning("%s interfaces without mac address were not included", unusedintf)

        return interfaces

    def get_addresses_from_interface(self, interface):
        """ Get all address objects associated with a physical or virtual interface """
        if interface.count_ipaddresses == 0:
            return []

        if hasattr(interface, 'device'):
            all_addresses = self.netbox.ipam.ip_addresses.filter(interface_id=interface.id)
        elif hasattr(interface, 'virtual_machine'):
            all_addresses = self.netbox.ipam.ip_addresses.filter(vminterface_id=interface.id)
        else:
            logging.warning('Unsupported interface type for interface "%s"', interface)
            return []

        ipv4_addresses = []
        for address in all_addresses:
            # We currently only support IPv4 addresses via broker assignment
            if address.family.value == 4:
                ipv4_addresses.append(address)
            else:
                logging.warning(
                    "Interface %s has an address (%s) in NetBox with an unsupported family (%s) which was ignored",
                    interface.name,
                    address.address,
                    address.family.label,
                )

        return ipv4_addresses
