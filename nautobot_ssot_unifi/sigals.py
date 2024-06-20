# pylint: disable=invalid-name
"""Nautobot signal handler functions for panorama_sync."""

import inspect

from django.apps import apps as global_apps

from nautobot_ssot_unifi.const import UNIFI_MANUFACTURER, UNIFI_MAP, UNIFI_SSOT_TAG


def _is_unifi_model(model_module, nautobot_model):
    def predicate(obj):
        if not inspect.isclass(obj) or obj.__module__ != model_module.__name__:
            return False
        return issubclass(obj, nautobot_model)

    return predicate


def nautobot_database_ready_callback(
    apps=global_apps, **kwargs
):  # pylint:disable=too-many-locals,import-outside-toplevel
    """Create models needed for this SSoT integration."""
    from nautobot_ssot.contrib import NautobotModel
    from nautobot_ssot_unifi.ssot import models

    predicate = _is_unifi_model(models, NautobotModel)
    ContentType = apps.get_model("contenttypes", "contenttype")
    CustomField = apps.get_model("extras", "customfield")

    Tag = apps.get_model("extras", "tag")
    tag, _ = Tag.objects.get_or_create(name=UNIFI_SSOT_TAG)
    for _, cls in inspect.getmembers(models, predicate):
        content_type = ContentType.objects.get_for_model(cls._model)  # pylint:disable=protected-access
        tag.content_types.add(content_type)

    Platform = apps.get_model("dcim", "platform")
    Manufacturer = apps.get_model("dcim", "manufacturer")
    Device = apps.get_model("dcim", "device")
    Interface = apps.get_model("dcim", "interface")

    custom_field, _ = CustomField.objects.get_or_create(
        label="Unifi Port ID",
        key="unifi_port_id",
        type="integer",
    )
    custom_field.content_types.add(ContentType.objects.get_for_model(Interface))

    manufacturer, _ = Manufacturer.objects.get_or_create(name=UNIFI_MANUFACTURER)

    content_type = ContentType.objects.get_for_model(Device)
    Role = apps.get_model("extras", "role")
    for info in UNIFI_MAP.values():
        role, _ = Role.objects.get_or_create(name=info["role"])
        role.content_types.add(content_type)
        Platform.objects.update_or_create(
            name=info["platform"],
            manufacturer=manufacturer,
            defaults={"napalm_driver": info["napalm_driver"]},
        )
