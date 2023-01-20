"""
This script allows you to create a VM, an interface and primary IP address
all in one screen.

Workaround for issues:
https://github.com/netbox-community/netbox/issues/1492
https://github.com/netbox-community/netbox/issues/648
"""

# pylint: disable=missing-function-docstring,too-few-public-methods,import-error,missing-class-docstring

from dcim.models import DeviceRole, Platform
from django.core.exceptions import ObjectDoesNotExist
from extras.models import Tag
from extras.scripts import Script, StringVar, IPAddressWithMaskVar, ObjectVar
from extras.scripts import MultiObjectVar, ChoiceVar, IntegerVar, TextVar
from ipam.choices import IPAddressStatusChoices
from ipam.models import IPAddress
from tenancy.models import Tenant
from virtualization.choices import VirtualMachineStatusChoices
from virtualization.models import Cluster, VirtualMachine, VMInterface


field_config = {
    'dns_name': {'required': False},
    'vm_tags': {'required': False},
    'primary_ip4': {'required': False},
    'primary_ip6': {'required': False},
    'role': {'required': False},
    'tenant': {'required': False},
    'platform': {'required': False},
    'interface_name': {'default': 'eth0'},
    'mac_address': {'required': False},
    'vcpus': {'required': False},
    'memory': {'required': False},
    'disk': {'required': False},
    'comments': {'required': False},
}

# Allow the field configuration to be customised by a site specific YAML file
# For example:
# ---
# dns_name:
#    required: True
#
# interface_name:
#     regex: '^eth[0-9]+$'
# ---
try:
    field_config_custom = Script().load_yaml('create_vm.yaml')
    if isinstance(field_config_custom, dict):
        # Merge field configuration, but don't allow arbitrary fields to be added to the YAML file
        for field_name, field_properties in field_config.items():
            if field_name in field_config_custom:
                field_properties.update(field_config_custom[field_name])
except FileNotFoundError:
    pass


class NewVM(Script):
    class Meta:
        name = "New VM"
        description = "Create a new VM"

    vm_name = StringVar(label="VM name")
    dns_name = StringVar(label="DNS name", **field_config['dns_name'])
    vm_tags = MultiObjectVar(model=Tag, label="VM tags", **field_config['vm_tags'])
    primary_ip4 = IPAddressWithMaskVar(label="IPv4 address", **field_config['primary_ip4'])
    primary_ip6 = IPAddressWithMaskVar(label="IPv6 address", **field_config['primary_ip6'])
    role = ObjectVar(model=DeviceRole, query_params=dict(vm_role=True), **field_config['role'])
    status = ChoiceVar(VirtualMachineStatusChoices, default=VirtualMachineStatusChoices.STATUS_ACTIVE)
    cluster = ObjectVar(model=Cluster)
    tenant = ObjectVar(model=Tenant, **field_config['tenant'])
    platform = ObjectVar(model=Platform, **field_config['platform'])
    interface_name = StringVar(**field_config['interface_name'])
    mac_address = StringVar(label="MAC address", **field_config['mac_address'])
    vcpus = IntegerVar(label="VCPUs", **field_config['vcpus'])
    memory = IntegerVar(label="Memory (MB)", **field_config['memory'])
    disk = IntegerVar(label="Disk (GB)", **field_config['disk'])
    comments = TextVar(label="Comments", **field_config['comments'])

    def run(self, data, commit):  # pylint: disable=unused-argument
        virtual_machine = VirtualMachine(
            name=data["vm_name"],
            role=data["role"],
            status=data["status"],
            cluster=data["cluster"],
            platform=data["platform"],
            vcpus=data["vcpus"],
            memory=data["memory"],
            disk=data["disk"],
            comments=data["comments"],
            tenant=data.get("tenant"),
        )
        virtual_machine.full_clean()
        virtual_machine.save()
        virtual_machine.tags.set(data["vm_tags"])

        vm_interface = VMInterface(
            name=data["interface_name"],
            mac_address=data["mac_address"],
            virtual_machine=virtual_machine,
        )
        vm_interface.full_clean()
        vm_interface.save()

        def add_addr(addr, family):
            if not addr:
                return
            if addr.version != family:
                raise RuntimeError(f"Wrong family for {addr}")
            try:
                ip_address = IPAddress.objects.get(
                    address=addr,
                )
                result = "Assigned"
            except ObjectDoesNotExist:
                ip_address = IPAddress(
                   address=addr,
                )
                result = "Created"
            ip_address.status = IPAddressStatusChoices.STATUS_ACTIVE
            ip_address.dns_name = data["dns_name"]
            if ip_address.assigned_object:
                raise RuntimeError(f"Address {addr} is already assigned")
            ip_address.assigned_object = vm_interface
            ip_address.tenant = data.get("tenant")
            ip_address.full_clean()
            ip_address.save()
            self.log_info(f"{result} IP address {ip_address.address} {ip_address.vrf or ''}")
            setattr(virtual_machine, f"primary_ip{family}", ip_address)

        add_addr(data["primary_ip4"], 4)
        add_addr(data["primary_ip6"], 6)
        virtual_machine.full_clean()
        virtual_machine.save()
        self.log_success(f"Created VM [{virtual_machine.name}](/virtualization/virtual-machines/{virtual_machine.id}/)")
