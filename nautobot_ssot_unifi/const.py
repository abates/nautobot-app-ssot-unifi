"""Constant definitions."""

from nautobot.dcim.choices import InterfaceTypeChoices

UNIFI_MANUFACTURER = "Ubiquiti Networks"

UNIFI_MAP = {
    "uap": {
        "platform": "Unifi AP",
        "role": "Access-Point",
        "napalm_driver": "napalm_unifi.uap",
    },
    "usw": {
        "platform": "Unifi Switch",
        "role": "Switch",
        "napalm_driver": "napalm_unifi.usw",
    },
    "usw_flex": {
        "platform": "Unifi Switch Flex",
        "role": "Switch",
        "napalm_driver": "napalm_unifi.usw_flex",
    },
    "usw_lite": {
        "platform": "Unifi Switch Lite",
        "role": "Switch",
        "napalm_driver": "napalm_unifi.usw_lite",
    },
    "ugw": {
        "platform": "Unifi Security Gateway",
        "role": "Firewall",
        "napalm_driver": "napalm_unifi.usg",
    },
}

UNIFI_SSOT_TAG = "unifi-ssot"

UNIFI_SSOT_INTERFACE_TYPES = {
    "ge": InterfaceTypeChoices.TYPE_1GE_FIXED,
    "sfp": InterfaceTypeChoices.TYPE_1GE_SFP,
    "other": InterfaceTypeChoices.TYPE_OTHER,
}
