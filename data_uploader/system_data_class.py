from dataclasses import dataclass

@dataclass
class SystemDataClass:
    """
    Class for keeping track of server properties
    """
    manufacturer: str
    model: str
    primaryMAC: str
    hostname: str
    serviceTag: str
    ipmiIPAddress: str

