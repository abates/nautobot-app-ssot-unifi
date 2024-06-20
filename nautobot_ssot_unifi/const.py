"""Constant definitions."""

from nautobot.dcim.choices import InterfaceTypeChoices

UNIFI_MANUFACTURER = "Ubiquiti Networks"

UNIFI_ROLE_MAP = {
    "uap": "Access-Point",
    "usw": "Switch",
    "ugw": "Firewall",
}

UNIFI_SSOT_TAG = "unifi-ssot"

UNIFI_SSOT_INTERFACE_TYPES = {
    "ge": InterfaceTypeChoices.TYPE_1GE_FIXED,
    "sfp": InterfaceTypeChoices.TYPE_1GE_SFP,
    "other": InterfaceTypeChoices.TYPE_OTHER,
}
