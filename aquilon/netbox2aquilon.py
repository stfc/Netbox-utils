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
        logging.info('Calling %s', cmd[0])
        logging.debug(
            'Calling "%s %s"',
            self.config['aquilon']['cli_path'],
            ' '.join(cmd),
        )
        process = subprocess.run(
            [self.config['aquilon']['cli_path']] + cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        logging.debug(
            'Commmand "%s %s" exited with code %d',
            self.config['aquilon']['cli_path'],
            ' '.join(cmd),
            process.returncode,
        )
        if process.stdout:
            logging.info(process.stdout.decode('utf-8').strip())
        if process.stderr:
            logging.warning(process.stderr.decode('utf-8').strip())
        if not process.stdout and not process.stderr:
            logging.debug(
                'Commmand "%s %s" returned no data',
                self.config['aquilon']['cli_path'],
                ' '.join(cmd),
            )
            return -1
        return process.returncode

    def _call_aq_cmds(self, cmds, dryrun=False):
        cmds_committed = []
        for cmd in cmds:
            if dryrun:
                print('# aq ' + ' '.join(cmd))
            else:
                retval = self._call_aq(cmd)
                if retval > 0:
                    logging.error(
                        'Commmand "%s %s" exited with error code %d',
                        self.config['aquilon']['cli_path'],
                        ' '.join(cmd),
                        retval,
                    )
                    return cmds_committed
                cmds_committed.append(cmd)
        return cmds_committed

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
        if device.primary_ip4 is None:
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

        cmds.append([
            'add_machine',
            '--machine', f'{device.aq_machine_name}',
            '--model', f'{device.device_type.slug}',
            '--rack', f'{rack_name}',
        ])

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

        cmds.append([
            'add_machine',
            '--machine', f'{virtual_machine.aq_machine_name}',
            '--vendor', 'virtual',
            '--model', 'vm-vmware',
            '--cluster', f'{cluster_name}',
            '--cpuname', f'{self.config["aquilon"]["cpuname"]}',
            '--cpuspeed', f'{self.config["aquilon"]["cpuspeed"]}',
            '--cpucount', f'{int(virtual_machine.vcpus)}',
            '--memory', f'{virtual_machine.memory}',
        ])

        cmds.append([
            'add_disk',
            '--machine', f'{virtual_machine.aq_machine_name}',
            '--disk', 'sda',
            '--controller', 'sata',
            '--size', f'{virtual_machine.disk}',
            '--boot',
        ])

        return cmds

    def _netbox_copy_interfaces(self, device):
        cmds = []
        interfaces = self.get_interfaces_from_device(device)
        for interface in interfaces:
            is_boot_interface = False
            for tag in interface.tags:
                if tag.slug == 'bootable':
                    is_boot_interface = True

            cmd = [
                'add_interface',
                '--machine', f'{device.aq_machine_name}',
                '--mac', f'{interface.mac_address}',
                '--interface', f'{interface.name}',
            ]
            if (hasattr(interface, 'mgmt_only') and interface.mgmt_only and not is_boot_interface):
                # mgmt_only is only an attribute for physical devices
                # Valid values are: bonding, bridge, loopback, management, oa, physical, public, virtual, vlan
                cmd.extend(['--iftype', 'management'])

            cmds.append(cmd)

            if is_boot_interface:
                cmds.append([
                    'update_interface',
                    '--machine', f'{device.aq_machine_name}',
                    '--interface', f'{interface.name}',
                    '--boot',
                ])
        return cmds

    def _netbox_copy_addresses(self, device):
        cmds = []
        interfaces = self.get_interfaces_from_device(device)
        for interface in interfaces:
            addresses = self.get_addresses_from_interface(interface)
            for address in addresses:
                # Don't add the primary IP as add_host does this
                if address.address != device.primary_ip4.address:
                    # Remove prefix length as aquilon gets this from the network definition
                    address.address = address.address.split('/')[0]
                    cmd = [
                        'add_interface_address',
                        '--machine', f'{device.aq_machine_name}',
                        '--interface', f'{interface.name}',
                        '--ip', f'{address.address}',
                    ]
                    if address.dns_name:
                        cmd.extend(['--fqdn', f'{address.dns_name}'])
                    if address.vrf:
                        cmd.extend(['--network_environment', f'{address.vrf}'])
                    cmds.append(cmd)
        return cmds

    def _netbox_get_personality(self, device, archetype, personality=None):
        if not personality:
            personality = 'inventory'

            logging.debug('Personality not specified, generating one from role and tenant')
            if device.tenant:
                if hasattr(device, 'device_role') and device.device_role:
                    # i.e. dcim.Devices
                    personality = f'{device.device_role.slug}-{device.tenant.slug}'
                elif hasattr(device, 'role') and device.role:
                    # i.e. virtualization.VirtualMachines
                    personality = f'{device.role.slug}-{device.tenant.slug}'
                else:
                    logging.debug('Device has no role, falling back to "inventory"')
            else:
                logging.debug('Device has no tenant, falling back to "inventory"')

        # Fall back to inventory personality if specific personality can't be found
        cmd_show_personality = ['show_personality', '--archetype', archetype, '--personality', personality]
        if self._call_aq(cmd_show_personality) != 0:
            logging.warning('Personality "%s" not found, falling back to "inventory"', personality)
            personality = 'inventory'

        return personality

    def netbox_copy(self, opts):
        """ Copy a device from NetBox to Aquilon """
        device = self._netbox_get_device(opts)

        aqdesttype = None
        aqdestval = None

        if opts.sandbox:
            aqdesttype = 'sandbox'
            aqdestval = opts.sandbox
        elif opts.domain:
            aqdesttype = 'domain'
            aqdestval = opts.domain

        # Preserve MagDB style machine naming for migrated hosts
        # Add a property to the object to store the desired aquilon machine name
        device.aq_machine_name = None
        if 'magdb2netbox' in [t.slug for t in device.tags]:
            device.aq_machine_name = f'system{device.custom_fields["magdb_system_id"]}'

        if isinstance(device, pynetbox.models.dcim.Devices):
            if device.aq_machine_name is None:
                device.aq_machine_name = f'netbox-{device.id}'
            cmds = self._netbox_copy_device(device)
        elif isinstance(device, pynetbox.models.virtualization.VirtualMachines):
            if device.aq_machine_name is None:
                device.aq_machine_name = f'netboxvm-{device.id}'
            cmds = self._netbox_copy_vm(device)
        else:
            logging.error('Unsupported device type to copy "%s"', type(device))
            sys.exit(1)

        personality = self._netbox_get_personality(device, opts.archetype)

        if not personality:
            logging.error('Unable to determine personality of device "%s"', type(device))
            sys.exit(1)

        cmds.extend(self._netbox_copy_interfaces(device))

        # Finally add the host to the machine
        cmds.append([
            'add_host',
            '--hostname', f'{device.primary_ip4.dns_name}',
            '--machine', f'{device.aq_machine_name}',
            '--archetype', f'{opts.archetype}',
            '--ip', f'{device.primary_ip4.address.split("/")[0]}',
            '--personality', f'{personality}',
            f'--{aqdesttype}', f'{aqdestval}',
            '--osname', f'{opts.osname}',
            '--osversion', f'{opts.osversion}',
        ])

        # Add additional addresses to non-primary interfaces
        cmds.extend(self._netbox_copy_addresses(device))

        cmds_executed = self._call_aq_cmds(cmds, dryrun=opts.dryrun)

        if not cmds_executed:
            logging.error('All commands failed, nothing to undo')
            sys.exit(1)

        if cmds_executed == cmds:
            sys.exit(0)

        logging.error('Command failed, attempting to undo changes')
        logging.debug('Commands executed: %s', cmds_executed)

        cmds_undo = self._undo_cmds(cmds_executed)
        logging.debug('Commands to run: %s', cmds_undo)

        cmds_undone = self._call_aq_cmds(cmds_undo, dryrun=opts.dryrun)
        logging.debug('Commands undone: %s', cmds_undone)

        if cmds_undone == cmds_undo:
            logging.info('All commands undone')
            sys.exit(1)

        logging.error('Unable to undo all commands')
        sys.exit(1)

    @classmethod
    def _undo_cmds(cls, cmds_run):
        cmds_undone = []

        # Map of required arguments for delete commands
        cmd_map = {
            'del_disk': ['--machine', '--disk'],
            'del_host': ['--hostname'],
            'del_interface': ['--interface', '--machine'],
            'del_interface_address': ['--machine', '--interface', '--ip'],
            'del_machine': ['--machine'],
        }

        # Iterate over the list of commands that have been run and generate commands that undo them
        # Only "add" commands actually need to be undone
        for cmd in cmds_run:
            action = cmd[0].replace('add_', 'del_')
            if action in cmd_map:
                cmd_undo = [action]
                for i, arg in enumerate(cmd):
                    if arg in cmd_map[action]:
                        cmd_undo.extend([cmd[i], cmd[i+1]])
                cmds_undone.append(cmd_undo)

        cmds_undone.reverse()
        return cmds_undone


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
        "--osversion", default=netbox2aquilon.config['aquilon']['osversion'],
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
