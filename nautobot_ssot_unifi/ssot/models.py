"""Nautobot DiffSync models for Unifi SSoT."""

from typing import TYPE_CHECKING, Annotated
import uuid

from nautobot_ssot.contrib import NautobotModel, CustomFieldAnnotation

from nautobot.extras.models import Tag, Status
from nautobot.dcim.models import DeviceType, Device, Location, ControllerManagedDeviceGroup, Interface
from nautobot.ipam.models import IPAddress, Prefix, IPAddressToInterface
from nautobot.ipam.choices import PrefixTypeChoices

from nautobot_ssot_unifi.const import UNIFI_MANUFACTURER, UNIFI_SSOT_TAG

if TYPE_CHECKING:
    from nautobot_ssot_unifi.ssot.adapters import UnifiNautobotAdapter


class ActiveStatusMixin:
    """A mixin that sets the status to active upon creation."""

    @classmethod
    def create(cls, diffsync: "UnifiNautobotAdapter", ids, attrs):
        """This overridden method makes sure to set the object status as `Active` when created."""
        attrs["status_id"] = Status.objects.get(name="Active").id
        return super().create(diffsync, ids, attrs)


class UnifiModelMixin:
    """Mixin to provide standard functionality for all Unifi Nautobot models."""

    @classmethod
    def get_queryset(cls):
        """All synchronized objects are tagged with the UNIFI_SSOT_TAG."""
        return super().get_queryset().filter(tags__name=UNIFI_SSOT_TAG)

    @classmethod
    def create(cls, diffsync: "UnifiNautobotAdapter", ids, attrs):
        """Create will either create or update a Nautobot object.

        This method will first look for a corresponding object in the
        database (by identifier). If found, rather than "creating" a
        new object the existing object will be tagged with the UNIFI_SSOT_TAG
        and then updated with the attributes. If not found then
        the object is created.

        Args:
            diffsync (UnifiNautobotAdapter): The diffsync adapter.
            ids (dict): Dictionary of fields and values to find the object.
            attrs (dict): Dictionary of fields and values that need to be assigned.

        Returns:
            NautobotModel: The diffsync model created/updated.
        """
        try:
            obj = cls._model.objects.get(**ids)
            obj.tags.add(Tag.objects.get(name=UNIFI_SSOT_TAG))
            return cls(**{**ids, **attrs, "pk": obj.pk})
        except cls._model.DoesNotExist:
            model = super().create(diffsync, ids, attrs)
            cls._model.objects.get(**ids).tags.add(Tag.objects.get(name=UNIFI_SSOT_TAG))
            return model

    def delete(self):
        """Remove the UNIFI_SSOT_TAG from a model.

        Returns:
            NautobotModel: Returns `self`
        """
        self.get_from_db().tags.remove(Tag.objects.get(name=UNIFI_SSOT_TAG))
        if getattr(self, "_perform_delete", False):
            return super().delete()
        return self


class SiteModel(ActiveStatusMixin, UnifiModelMixin, NautobotModel):
    """Location model for sites."""

    _model = Location
    _modelname = "site"
    _identifiers = ("name",)
    _attributes = ("location_type__name",)

    name: str
    status_id: uuid.UUID = None
    location_type__name: str = ""


class DeviceTypeModel(UnifiModelMixin, NautobotModel):
    """DeviceType model."""

    _model = DeviceType
    _modelname = "device_type"
    _identifiers = (
        "manufacturer__name",
        "model",
    )
    _attributes = ("part_number",)

    manufacturer__name: str = UNIFI_MANUFACTURER
    model: str

    part_number: str = ""


class DeviceModel(ActiveStatusMixin, UnifiModelMixin, NautobotModel):
    """Device model."""

    _model = Device
    _modelname = "device"
    _identifiers = (
        "name",
        "controller_managed_device_group__name",
        "controller_managed_device_group__controller__name",
    )
    _attributes = (
        "device_type__model",
        "role__name",
        "location__name",
        "serial",
        "platform__name",
        "primary_ip4__host",
        "primary_ip6__host",
    )
    _perform_delete = True

    name: str
    controller_managed_device_group__name: str = None
    controller_managed_device_group__controller__name: str = None
    device_type__model: str
    role__name: str
    location__name: str
    serial: str
    platform__name: str
    primary_ip4__host: str = None
    primary_ip6__host: str = None

    status_id: uuid.UUID = None

    @classmethod
    def create(cls, diffsync: "UnifiNautobotAdapter", ids, attrs):
        """Create the device.

        This overridden method removes the primary IP addresses since those
        cannot be set until after the interfaces are created. The primary IPs
        are set in the `sync_complete` callback of the adapter.

        Args:
            diffsync (UnifiNautobotAdapter): The nautobot sync adapter.
            ids (dict[str, Any]): The natural keys for the device.
            attrs (dict[str, Any]): The attributes to assign to the newly created
                device.

        Returns:
            DeviceModel: The device model.
        """
        if attrs["primary_ip4__host"] or attrs["primary_ip6__host"]:
            diffsync._primary_ips.append(
                {
                    "device": {**ids},
                    "primary_ip4": attrs.pop("primary_ip4__host", None),
                    "primary_ip6": attrs.pop("primary_ip4__host", None),
                }
            )
        return super().create(diffsync, ids, attrs)


class DeviceGroupModel(UnifiModelMixin, NautobotModel):
    """DeviceGroup model."""

    _model = ControllerManagedDeviceGroup
    _modelname = "device_group"
    _identifiers = (
        "controller__name",
        "name",
    )
    _attributes = tuple()

    controller__name: str
    name: str


class InterfaceModel(ActiveStatusMixin, UnifiModelMixin, NautobotModel):
    """DeviceGroup model."""

    _model = Interface
    _modelname = "interface"
    _identifiers = (
        "label",
        "device__name",
        "device__controller_managed_device_group__name",
        "device__controller_managed_device_group__controller__name",
    )

    _attributes = (
        "type",
        "unifi_port_id",
    )
    _perform_delete = True

    label: str
    name: str = ""
    device__name: str
    device__controller_managed_device_group__name: str
    device__controller_managed_device_group__controller__name: str

    type: str
    unifi_port_id: Annotated[int, CustomFieldAnnotation(name="unifi_port_id")] = None

    status_id: uuid.UUID = None

    @classmethod
    def create(cls, diffsync: "UnifiNautobotAdapter", ids, attrs):
        """Create a new interface.

        This overridden create will set the interface name. That way the interface name
        can be changed (so that Napalm stuff matches Nautobot) but the ssot job
        can still find the interfaces.
        """
        attrs["name"] = ids["label"]
        return super().create(diffsync, ids, attrs)


class PrefixModel(ActiveStatusMixin, UnifiModelMixin, NautobotModel):
    """DiffSync model for Prefix."""

    _model = Prefix
    _modelname = "prefix"
    _identifiers = ("network", "prefix_length")
    _attributes = tuple()

    network: str
    prefix_length: int

    status_id: uuid.UUID = None
    type: str = None

    @classmethod
    def create(cls, diffsync: "UnifiNautobotAdapter", ids, attrs):
        """This overridden method makes sure to set the prefix type when created."""
        attrs["type"] = PrefixTypeChoices.TYPE_NETWORK
        return super().create(diffsync, ids, attrs)


class IPAddressModel(ActiveStatusMixin, UnifiModelMixin, NautobotModel):
    """DiffSync model for IP Addresses."""

    _model = IPAddress
    _modelname = "ip_address"
    _identifiers = (
        "host",
        "mask_length",
    )
    _attributes = (
        "parent__network",
        "parent__prefix_length",
    )

    host: str
    mask_length: int
    parent__network: str
    parent__prefix_length: int

    status_id: uuid.UUID = None


class IPAddressToInterfaceModel(NautobotModel):
    """DiffSync model for assigning IP Addresses to interfaces."""

    _model = IPAddressToInterface
    _modelname = "ip_address_to_interface"
    _identifiers = (
        "ip_address__host",
        "interface__label",
        "interface__device__name",
        "interface__device__controller_managed_device_group__name",
        "interface__device__controller_managed_device_group__controller__name",
    )

    _attributes = tuple()

    ip_address__host: str
    interface__label: str
    interface__device__name: str
    interface__device__controller_managed_device_group__name: str
    interface__device__controller_managed_device_group__controller__name: str
