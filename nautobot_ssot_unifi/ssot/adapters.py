"""Adapters for diffsync models between Unifi and Nautobot."""

from typing import Any, Dict, List
from diffsync import DiffSync

from asgiref.sync import sync_to_async, async_to_sync

from diffsync.diff import Diff
from diffsync.enum import DiffSyncFlags
from nautobot.apps.jobs import Job
from nautobot.dcim.models import Device
from nautobot.ipam.models import IPAddress

from nautobot_ssot.contrib import NautobotAdapter
from structlog import BoundLogger

from nautobot_ssot_unifi.const import UNIFI_MAP, UNIFI_SSOT_INTERFACE_TYPES
from nautobot_ssot_unifi.ssot import models

from nautobot_ssot_unifi.unifi import Client

from netaddr import IPNetwork


class UnifiAdapterMixin:
    """Code common to both adapters."""

    site = models.SiteModel
    device_group = models.DeviceGroupModel
    device_type = models.DeviceTypeModel
    device = models.DeviceModel
    interface = models.InterfaceModel
    prefix = models.PrefixModel
    ip_address = models.IPAddressModel
    ip_address_to_interface = models.IPAddressToInterfaceModel

    top_level = (
        "site",
        "prefix",
        "ip_address",
        "device_group",
        "device_type",
        "device",
        "interface",
        "ip_address_to_interface",
    )


class UnifiNautobotAdapter(UnifiAdapterMixin, NautobotAdapter):
    """Adapter to connect to Nautobot."""

    _primary_ips: List[Dict[str, Any]]

    def __init__(self, *args, job, sync=None, **kwargs):
        """Initialize the adapter."""
        super().__init__(*args, job=job, sync=sync, **kwargs)
        self._primary_ips = []

    def sync_complete(
        self, source: DiffSync, diff: Diff, flags: DiffSyncFlags = DiffSyncFlags.NONE, logger: BoundLogger | None = None
    ) -> None:
        """Update devices with their primary IPs once the sync is complete."""
        for info in self._primary_ips:
            device = Device.objects.get(**info["device"])
            for ip in ["primary_ip4", "primary_ip6"]:
                if info[ip]:
                    setattr(device, ip, IPAddress.objects.get(host=info[ip]))
            device.validated_save()


class UnifiAdapter(UnifiAdapterMixin, DiffSync):
    """Adapter to connect to Unifi."""

    def __init__(
        self, *args, job: Job, controller_name: str, default_location_type: str, default_location_name: str, **kwargs
    ):
        """Initialize the unifi source adapter.

        This adapter will read data from a Unifi Controller and create
        diffsync models based on the data received.

        Args:
            *args: Additional positional arguments needed by the parent DiffSync adapter.
            job (Job): The Nautobot job instance that is running this sync.
            controller_name (str): The device controller name.
            default_location_type (str): The name of the location type to use when creating new locations.
            default_location_name (str): The name of the location to use when the Unifi site is `default`.
            **kwargs: Additional keyword arguments needed by the parent DiffSync adapter.
        """
        super(*args, **kwargs).__init__()
        self.job = job
        self.controller_name = controller_name
        self.default_location_type = default_location_type
        self.default_location_name = default_location_name
        self.debug = kwargs.get("debug", False)

    @sync_to_async
    def _debug(self, *args, **kwargs):
        self.job.logger.debug(*args, **kwargs)

    @sync_to_async
    def _info(self, *args, **kwargs):
        self.job.logger.info(*args, **kwargs)

    def _create_interface(self, device, interface_name, interface_type, port_id):
        return self.interface(
            **{f"device__{key}": value for key, value in device.get_identifiers().items()},
            label=interface_name,
            type=interface_type,
            unifi_port_id=port_id,
        )

    async def _assign_ip(self, ip: str, netmask: str, interface: str) -> IPNetwork:
        ip_address = IPNetwork(f"{ip}/{netmask}")
        prefix, created = self.get_or_add_model_instance(
            self.prefix(
                network=str(ip_address.network),
                prefix_length=ip_address.prefixlen,
            )
        )
        if created:
            await self._debug("Added prefix %s", prefix)

        _, created = self.get_or_add_model_instance(
            self.ip_address(
                host=str(ip_address.ip),
                mask_length=ip_address.prefixlen,
                parent__network=str(ip_address.network),
                parent__prefix_length=ip_address.prefixlen,
            )
        )
        if created:
            self.add(interface)
            assignment = self.ip_address_to_interface(
                **{f"interface__{key}": value for key, value in interface.get_identifiers().items()},
                ip_address__host=ip,
            )
            self.add(assignment)
        return ip_address

    @async_to_sync
    async def load(self, host, port, username, password, verify_cert, timeout):
        """Asynchronously load data from unifi."""
        self.client = Client(
            host=host,
            port=port,
            username=username,
            password=password,
            verify_cert=verify_cert,
            timeout=timeout,
        )
        self._info("Loading data from the Unifi Controller %s", self.job.controller)
        self.add(
            self.device_group(
                name="default",
                controller__name=self.controller_name,
            )
        )
        for site in await self.client.get_sites():
            site_name = site.name
            self.client.site = site_name
            if site_name == "default":
                site_name = self.default_location_name
                location_type__name = self.default_location_type
            site = self.site(name=site_name, location_type__name=location_type__name)
            await self._debug("Added site %s", site)
            self.add(site)

            for unifi_device in await self.client.get_devices():
                unifi_info = self.job.hardware_models[unifi_device.model]
                unifi_type = unifi_info["type"]
                if unifi_type == "usw":
                    if "lite" in unifi_info["name"].lower():
                        unifi_type = "usw_lite"
                    elif "flex" in unifi_info["name"].lower():
                        unifi_type = "usw_flex"

                device_type = self.device_type(
                    model=unifi_device.model,
                    part_number=unifi_info["sku"],
                )
                _, created = self.get_or_add_model_instance(device_type)
                if created:
                    await self._debug("Added device type %s", device_type)

                device = self.device(
                    name=unifi_device.name,
                    controller_managed_device_group__name="default",
                    controller_managed_device_group__controller__name=self.job.controller.name,
                    location__name=site.name,
                    device_type__model=unifi_device.model,
                    role__name=UNIFI_MAP[unifi_type]["role"],
                    serial=unifi_device.raw["serial"],
                    platform__name=UNIFI_MAP[unifi_type]["platform"],
                )
                await self._debug("Adding device %s", device)
                self.add(device)
                for port in unifi_device.raw["port_table"]:
                    interface = self._create_interface(
                        device,
                        port["name"],
                        UNIFI_SSOT_INTERFACE_TYPES[port.get("media", "other").lower()],
                        port["port_idx"],
                    )
                    if "ip" in port:
                        await self._assign_ip(port["ip"], port["netmask"], interface)
                    else:
                        self.add(interface)

                if unifi_device.raw["config_network"] and unifi_device.raw["config_network"]["type"] == "static":
                    interface = self._create_interface(device, "mgmt", UNIFI_SSOT_INTERFACE_TYPES["other"], -1)
                    await self._debug("Setting management interface info: %s", unifi_device.raw["config_network"])
                    ip_address = await self._assign_ip(
                        unifi_device.raw["config_network"]["ip"],
                        unifi_device.raw["config_network"]["netmask"],
                        interface,
                    )
                    if ip_address.version == 4:
                        device.primary_ip4__host = str(ip_address.ip)
                    else:
                        device.primary_ip6__host = str(ip_address.ip)
