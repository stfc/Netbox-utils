#!/usr/bin/env python3

""" netboxdump_subnetdata """

import argparse
import logging
import os.path

from json import dump

import coloredlogs

from scd_netbox import SCDNetbox


class NetboxDumpSubnetdata(SCDNetbox):
    """ Extends base SCDNetbox class with functionality to dump subnets to a file """

    def _get_subnet_fields(self):
        results = []
        for prefix in self.netbox.ipam.prefixes.filter(tenant_id=(7, 8, 31), family=4):
            fields = {
                'UDF': {}
            }
            address, mask = prefix.prefix.split('/', 2)
            fields['SubnetAddress'] = address
            fields['SubnetMask'] = mask
            fields['SubnetName'] = prefix.description
            if prefix.role:
                fields['UDF']['TYPE'] = prefix.role.name
            if prefix.site:
                fields['UDF']['LOCATION'] = prefix.site.name
            if prefix.vrf:
                fields['UDF']['VRF'] = prefix.vrf.name

            if not fields['UDF']:
                del fields['UDF']

            results.append(fields)
        return results

    def write_subnetdata_txt(self, directory):
        """
        Format of subnetdata.txt:
            - Fields are separated by tabs
            - A field is a key/value pair, separated by a space
            - The value of the DefaultRouters field is a comma-separated list of IP addresses
            - The value of the UDF field is a list of "<key>=<value>" pairs, separated by ';'
        """
        lines = []
        subnet_fields = self._get_subnet_fields()
        for fields in subnet_fields:
            if 'UDF' in fields:
                fields['UDF'] = ';'.join([k + '=' + v for k, v in fields['UDF'].items()])
            fields = [' '.join(pair) for pair in fields.items()]
            fields.sort()
            lines.append('\t'.join(fields)+'\n')

        with open(os.path.join(directory, 'subnetdata.txt'), 'w', encoding='utf-8') as dumpfile:
            dumpfile.writelines(lines)

    def write_subnetdata_json(self, directory):
        """ Dump subnetdata field structure in JSON format """
        subnet_fields = self._get_subnet_fields()
        with open(os.path.join(directory, 'subnetdata.json'), 'w', encoding='utf-8') as dumpfile:
            dump(subnet_fields, dumpfile)


def _main():
    logging.basicConfig(format='%(levelname)s: %(message)s')

    netbox_dump_subnetdata = NetboxDumpSubnetdata()

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--datarootdir",
        help="",
        required=True,
    )
    parser.add_argument(
        "--format", action='store', default='txt', choices=['txt', 'json'],
        help="Format of output file.",
    )
    parser.add_argument(
        "--audit", action='store_true', default='false',
        help="Does nothing, only present for compatability.",
    )
    parser.add_argument(
        "--debug", action='store_true',
        help="Enable debug logging.",
    )
    opts, _ = parser.parse_known_args()

    coloredlogs.install(fmt='%(levelname)7s: %(message)s')

    if opts.debug:
        coloredlogs.set_level(logging.DEBUG)

    if opts.format == 'txt':
        netbox_dump_subnetdata.write_subnetdata_txt(opts.datarootdir)
    elif opts.format == 'json':
        netbox_dump_subnetdata.write_subnetdata_json(opts.datarootdir)


if __name__ == "__main__":
    _main()
