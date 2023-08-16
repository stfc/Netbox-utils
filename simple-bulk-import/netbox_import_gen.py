#!/usr/bin/python3

import csv
import sys
import json

rawcsvpath = sys.argv[1]

hostdict = csv.DictReader(open(rawcsvpath), delimiter=",")

#create device list
devicetypes = []
devices = []
interfaces = []
ips = []
for importee in hostdict:
    print(importee)

    # Create Device Type
    devicetype = {}
    devicetype["manufacturer"] = importee["Manufacturer"]
    devicetype["model"] = importee["Device Type"]
    devicetype["slud"] = importee["Device Type"]
    devicetype["u_height"] = importee["Rack Units"]
    devicetypes.append(devicetype)

    # Create Device
    device = {}
    device["tenant"] = importee["Tenant"]
    device["device_role"] = importee["Role"]
    device["manufacturer"] = importee["Vendor"]
    device["device_type"] = importee["Device Type"]
    device["status"] = importee["Status"]
    device["site"] = importee["Site"]
    device["location"] = importee["Location"]
    device["rack"] = importee["Rack"]
    device["face"] = importee["face"]
    device["airflow"] = importee["airflow"]
    device["position"] = importee["Rack Position"]
    device["name"] = importee["FQDN"]
    device["serial"] = importee["Serial"]
    devices.append(device)

    # Create BMC Interface
    bmcinterface = {}
    bmcinterface["enabled"] = "TRUE"
    bmcinterface["mgmt_only"] = "TRUE"
    bmcinterface["type"] = "1000base-t"
    bmcinterface["name"] = "bmc0"
    bmcinterface["device"] = importee["FQDN"]
    bmcinterface["vrf"] = importee["BMC VRF"]
    bmcinterface["mac_address"] = importee["BMC MAC"]
    interfaces.append(bmcinterface)

    # Create First Eth interface
    ethinterface = {}
    ethinterface["enabled"] = "TRUE"
    ethinterface["mgmt_only"] = "False"
    ethinterface["type"] = importee["NIC 1 Type"]
    ethinterface["name"] = importee["NIC 1 Name"]
    ethinterface["device"] = importee["FQDN"]
    ethinterface["vrf"] = importee["NIC 1 VRF"]
    ethinterface["mac_address"] = importee["NIC 1 MAC"]
    interfaces.append(ethinterface)

    # Create BMC IP
    bmcip = {}
    bmcip["address"] = importee["BMC IP"]
    bmcip["status"] = "active"
    bmcip["tenant"] = importee["Tenant"]
    bmcip["interface"] = "bmc0"
    bmcip["device"] = importee["FQDN"]
    ips.append(bmcip)

    # Create First Eth IP
    ethip = {}
    ethip["address"] = importee["NIC 1 IP"]
    ethip["status"] = "active"
    ethip["tenant"] = importee["Tenant"]
    ethip["interface"] = importee["NIC 1 Name"]
    ethip["device"] = importee["FQDN"]
    ips.append(ethip)

#print(devicetypes)
#print(devices)
#print(interfaces)
#print(ips)

# Output device types json file
with open("devicetypes.json","w", encoding="utf-8") as outfile:
    outfile.write(json.dumps(devicetypes))

# Output devices json file
with open("devices.json","w", encoding="utf-8") as outfile:
    outfile.write(json.dumps(devices))

# Output Interfaces json file
with open("interfaces.json","w", encoding="utf-8") as outfile:
    outfile.write(json.dumps(interfaces))

# Output IPs json file
with open("ips.json","w", encoding="utf-8") as outfile:
    outfile.write(json.dumps(ips))
