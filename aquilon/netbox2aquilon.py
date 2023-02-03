#!/usr/bin/env python3

""" netbox2aquilon - script to extract data out of netbox and use it to create aquilon entities."""

import argparse
import logging
import os.path
import subprocess
import sys

import coloredlogs
import pynetbox

from scd_netbox import SCDNetbox


class Netbox2Aquilon(SCDNetbox):
    """ Extends base SCDNetbox class with aquilon specific functionality """

    @classmethod
    def get_current_sandbox(cls):
        """ Get owner and name of sandbox if command is being run while inside one """
        sandbox = None
        git_rev_parse = subprocess.run(
            ['git', 'rev-parse', '--show-toplevel'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if git_rev_parse.returncode == 0:
            owner = os.path.basename(os.path.dirname(git_rev_parse.stdout))
            name = os.path.basename(git_rev_parse.stdout.strip())
            if owner and name:
                sandbox = (owner + b'/' + name).decode('utf-8')
        return sandbox

    def _call_aq(self, cmd):
        process = subprocess.run(
            [self.config['aquilon']['cli_path']]+cmd.split(' '),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        logging.debug(
            'Calling %s %s',
            self.config['aquilon']['cli_path'],
            cmd,
        )
        if process.returncode != 0:
            logging.error(
                'Commmand %s %s exited with error code %d',
                self.config['aquilon']['cli_path'],
                cmd,
                process.returncode,
            )
            return process.returncode
        if not process.stdout and not process.stderr:
            logging.debug(
                'Commmand %s %s returned no data',
                self.config['aquilon']['cli_path'],
                cmd,
            )
            return -1
        return 0

    def _call_aq_cmds(self, cmds, dryrun=False):
        for cmd in cmds:
            if dryrun:
                print('aq ' + cmd)
            else:
                retval = self._call_aq(cmd)
                if retval > 0:
                    return retval
        return 0

    def _netbox_get_device(self, opts):
        if opts.magdb_id:
            device = self.get_device_by_magdb_id(opts.magdb_id)
        elif opts.netboxname:
            device = self.get_device_by_name(opts.netboxname)
        elif opts.hostname:
            device = self.get_device_by_hostname(opts.hostname)
        else:
            logging.error("No device specification provided")
            sys.exit(2)

        # check if device has a primary ip
        if device.primary_ip is None:
            logging.error("No primary IP defined for host")
            sys.exit(1)

        # check if device has a tenant
        if device.tenant is None:
            logging.error("No tenant defined for host")
            sys.exit(1)

        return device

    def _netbox_copy_device(self, device):
        cmds = []

        # check if host is in rack - query netbox for rack
        rack = self.get_rack_from_device(device)

        rack_delimeter = '-'  # Default naming convention for new racks
        if 'magdb2netbox' in [t.slug for t in rack.tags]:
            rack_delimeter = 'rack'  # Preserve magdb2aquilon style names for migrated racks

        rack_name = rack_delimeter.join([device.site.facility.lower(), rack.facility_id])

        cmds.append(' '.join([
            'add_machine',
            f'--machine {device.aq_machine_name}',
            f'--model {device.device_type.slug}',
            f'--rack {rack_name}',
        ]))

        return cmds

    def _netbox_copy_vm(self, virtual_machine):
        cmds = []

        if not virtual_machine.disk:
            logging.error('Cannot continue, virtual disk size not present.')
            sys.exit(1)

        # Use name of cluster by default, unless another name has been specified
        cluster_name = virtual_machine.cluster.name.lower().replace(' ', '_')
        cluster = self.netbox.virtualization.clusters.get(virtual_machine.cluster.id)
        if 'aq_name' in cluster.custom_fields:
            cluster_name = cluster.custom_fields['aq_name']

        cmds.append(' '.join([
            'add_machine',
            f'--machine {virtual_machine.aq_machine_name}',
            '--vendor virtual',
            '--model vm-vmware',
            f'--cluster {cluster_name}',
            f'--cpuname {self.config["aquilon"]["cpuname"]}',
            f'--cpuspeed {self.config["aquilon"]["cpuspeed"]}',
            f'--cpucount {int(virtual_machine.vcpus)}',
            f'--memory {virtual_machine.memory}',
        ]))

        cmds.append(' '.join([
            'add_disk',
            f'--machine {virtual_machine.aq_machine_name}',
            '--disk sda',
            '--controller sata',
            f'--size {virtual_machine.disk}',
            '--boot',
        ]))

        return cmds

    def _netbox_copy_interfaces(self, device):
        cmds = []
        interfaces = self.get_interfaces_from_device(device)
        for interface in interfaces:
            cmds.append((' '.join([
                'add_interface',
                f'--machine {device.aq_machine_name}',
                f'--mac {interface.mac_address}',
                f'--interface {interface.name}',
                # Valid values are: bonding, bridge, loopback, management, oa, physical, public, virtual, vlan
                # mgmt_only is only an attribute for physical devices
                '--iftype management'
                    if (hasattr(interface, 'mgmt_only') and interface.mgmt_only) else '',
            ])).strip())

            is_boot_interface = False
            for tag in interface.tags:
                if tag.slug == 'bootable':
                    is_boot_interface = True

            if is_boot_interface:
                cmds.append(' '.join([
                    'update_interface',
                    f'--machine {device.aq_machine_name}',
                    f'--interface {interface.name}',
                    '--boot',
                ]))
        return cmds

    def _netbox_copy_addresses(self, device):
        cmds = []
        interfaces = self.get_interfaces_from_device(device)
        for interface in interfaces:
            addresses = self.get_addresses_from_interface(interface)
            for address in addresses:
                # Don't add the primary IP as add_host does this
                if address.address != device.primary_ip.address:
                    # Remove prefix length as aquilon gets this from the network definition
                    address.address = address.address.split('/')[0]
                    cmd = [
                        'add_interface_address',
                        f'--machine {device.aq_machine_name}',
                        f'--interface {interface.name}',
                        f'--ip {address.address}',
                    ]
                    if address.dns_name:
                        cmd.append(f'--fqdn {address.dns_name}')
                    if address.vrf:
                        cmd.append(f'--network_environment {address.vrf}')
                    cmds.append(' '.join(cmd))
        return cmds

    def netbox_copy(self, opts):
        """ Copy a device from NetBox to Aquilon """
        device = self._netbox_get_device(opts)

        if opts.sandbox:
            aqdesttype = 'sandbox'
            aqdestval = opts.sandbox
        elif opts.domain:
            aqdesttype = 'domain'
            aqdestval = opts.domain

        # Preserve MagDB style machine naming for migrated hosts
        # Add a property to the object to store the desired aquilon machine name
        device.aq_machine_name = f'netbox-{device.id}'
        if 'magdb2netbox' in [t.slug for t in device.tags]:
            device.aq_machine_name = f'system{device.custom_fields["magdb_system_id"]}'

        if isinstance(device, pynetbox.models.dcim.Devices):
            cmds = self._netbox_copy_device(device)
            personality = f'{device.device_role.slug}-{device.tenant.slug}'
        elif isinstance(device, pynetbox.models.virtualization.VirtualMachines):
            cmds = self._netbox_copy_vm(device)
            personality = 'inventory'
            if device.role:
                personality = f'{device.role.slug}-{device.tenant.slug}'
        else:
            logging.error('Unsupported device type to copy "%s"', type(device))
            sys.exit(1)

        if not personality:
            logging.error('Unable to determine personality of device "%s"', type(device))
            sys.exit(1)

        cmds.extend(self._netbox_copy_interfaces(device))

        # Finally add the host to the machine
        cmds.append(' '.join([
            'add_host',
            f'--hostname {device.primary_ip.dns_name}',
            f'--machine {device.aq_machine_name}',
            f'--archetype {opts.archetype}',
            f'--ip {device.primary_ip.address.split("/")[0]}',
            f'--personality {personality}',
            f'--{aqdesttype} {aqdestval}',
            f'--osname {opts.osname}',
            f'--osversion {opts.osvers}',
        ]))

        # Add additional addresses to non-primary interfaces
        cmds.extend(self._netbox_copy_addresses(device))

        sys.exit(self._call_aq_cmds(cmds, dryrun=opts.dryrun))


def _main():
    logging.basicConfig(format='%(levelname)s: %(message)s')

    netbox2aquilon = Netbox2Aquilon(additonal_config_name='netbox2aquilon')

    parser = argparse.ArgumentParser()

    aqdest = parser.add_mutually_exclusive_group()
    aqdest.add_argument(
        "--sandbox", "-s",
        help="Name of the sandbox in user/sandbox format to add the copied host to",
    )
    aqdest.add_argument(
        "--domain", "-d",
        help="Name of the domain to add the copied host to",
    )

    hostid = parser.add_mutually_exclusive_group(required=True)
    hostid.add_argument(
        "--hostname",
        help="Fully qualified domain name of host to copy from Netbox.",
    )
    hostid.add_argument(
        "--netboxname", "-n",
        help="Name of device to copy from Netbox.",
    )
    hostid.add_argument(
        "--magdb_id", "-m",
        help="MagDB system ID of host to copy from Netbox.",
    )

    parser.add_argument(
        "--archetype", "-a", default=netbox2aquilon.config['aquilon']['archetype'],
        help=(
            "Destination aquilon archetype for the host to be copied. Default: " +
            netbox2aquilon.config['aquilon']['archetype']
        ),
    )
    parser.add_argument(
        "--osname", default=netbox2aquilon.config['aquilon']['osname'],
        help=(
            "Name of the Operating system on the host. Default: " +
            netbox2aquilon.config['aquilon']['osname']
        ),
    )
    parser.add_argument(
        "--osvers", default=netbox2aquilon.config['aquilon']['osversion'],
        help=(
            "Version of the Operating system on the host. Default: " +
            netbox2aquilon.config['aquilon']['osversion']
        ),
    )
    parser.add_argument(
        "--dryrun", action='store_true',
        help="Do not do anything to aquilon, instead print what would be done",
    )
    parser.add_argument(
        "--debug", action='store_true',
        help="Set logging level to debug.",
    )
    opts, _ = parser.parse_known_args()

    coloredlogs.install(fmt='%(levelname)7s: %(message)s')

    if opts.debug:
        coloredlogs.set_level(logging.DEBUG)

    # If domain or sandbox have not been provided, then see if the command is being run from sandbox,
    # if not, then use the domain configured as default.
    if not opts.domain and not opts.sandbox:
        opts.sandbox = netbox2aquilon.get_current_sandbox()
        if not opts.sandbox:
            opts.domain = netbox2aquilon.config['aquilon']['domain']

    netbox2aquilon.netbox_copy(opts)


if __name__ == "__main__":
    _main()
