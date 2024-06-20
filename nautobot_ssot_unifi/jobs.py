"""Jobs for Unifi SSoT integration."""

import csv
import logging
from os import path
from urllib.parse import urlparse

from django.core.exceptions import ValidationError

from nautobot.apps.jobs import BooleanVar, Job, ObjectVar, register_jobs

from nautobot.dcim.models import Controller, LocationType
from nautobot.extras.models import ExternalIntegration, SecretsGroup, SecretsGroupAssociation
from nautobot.extras.choices import SecretsGroupAccessTypeChoices, SecretsGroupSecretTypeChoices

from netutils.dns import fqdn_to_ip

from nautobot_ssot.jobs.base import DataSource

from nautobot_ssot_unifi.ssot import adapters

name = "Unifi SSoT"  # pylint: disable=invalid-name


class UnifiDataSource(DataSource, Job):
    """Unifi SSoT Data Source."""

    debug: bool = BooleanVar(description="Enable for more verbose debug logging", default=False)
    controller: Controller = ObjectVar(description="Unifi Controller to sync with", model=Controller)
    location_type: LocationType = ObjectVar(
        description="Default location type. If locations are added, this location type will be used for the new locations.",
        model=LocationType,
        required=False,
    )
    default_location: LocationType = ObjectVar(
        description="Override the 'default' site with this location. If not specified, the controller's location will be used.",
        model=LocationType,
        required=False,
    )

    class Meta:  # pylint: disable=too-few-public-methods
        """Meta data for Unifi."""

        name = "Unifi to Nautobot"
        data_source = "Unifi"
        data_target = "Nautobot"
        description = "Sync information from Unifi to Nautobot"
        has_sensitive_variables = False

    @classmethod
    def validate_data(cls, data, files=None):
        """Validate that the controller and secrets are appropriate for Unifi."""
        validated_data = super().validate_data(data, files)
        controller: Controller = validated_data["controller"]
        remote_url = controller.external_integration.remote_url
        url = urlparse(remote_url)
        if url.scheme not in ["http", "https"]:
            raise ValidationError(
                {
                    "controller": f"Unifi SSoT requires either HTTP or HTTPS for the external integration, not {url.scheme} that is currently specified in the remote url {remote_url}"
                }
            )

        try:
            secrets_group: SecretsGroup = controller.external_integration.secrets_group
            for secret_type in [
                SecretsGroupSecretTypeChoices.TYPE_USERNAME,
                SecretsGroupSecretTypeChoices.TYPE_PASSWORD,
            ]:
                secrets_group.get_secret_value(
                    access_type=SecretsGroupAccessTypeChoices.TYPE_HTTP, secret_type=secret_type
                )
        except SecretsGroupAssociation.DoesNotExist as error:
            raise ValidationError(
                {
                    "controller": "The controller's external integration must include a secrets group with HTTP username and password."
                }
            ) from error

        return validated_data

    def load_source_adapter(self):
        """Load data from Unifi into DiffSync models."""
        external_integration: ExternalIntegration = self.controller.external_integration
        url = urlparse(external_integration.remote_url)
        secrets_group: SecretsGroup = external_integration.secrets_group
        username = secrets_group.get_secret_value(
            access_type=SecretsGroupAccessTypeChoices.TYPE_HTTP, secret_type=SecretsGroupSecretTypeChoices.TYPE_USERNAME
        )
        password = secrets_group.get_secret_value(
            access_type=SecretsGroupAccessTypeChoices.TYPE_HTTP, secret_type=SecretsGroupSecretTypeChoices.TYPE_PASSWORD
        )

        default_location_name = self.default_location.name
        default_location_type = self.default_location.location_type.name
        self.source_adapter = adapters.UnifiAdapter(
            job=self,
            controller_name=self.controller.name,
            default_location_type=default_location_type,
            default_location_name=default_location_name,
        )
        self.source_adapter.load(
            host=fqdn_to_ip(url.hostname),
            port=(url.port or 443),
            username=username,
            password=password,
            verify_cert=external_integration.verify_ssl,
            timeout=external_integration.timeout,
        )

    def load_target_adapter(self):
        """Load data from Nautobot into DiffSync models."""
        self.target_adapter = adapters.UnifiNautobotAdapter(job=self, sync=self.sync)
        self.target_adapter.load()

    def run(
        self, dryrun, debug, controller, default_location, location_type, *args, **kwargs
    ):  # pylint: disable=arguments-differ,too-many-arguments,attribute-defined-outside-init
        """Perform data synchronization."""
        self.dryrun = dryrun
        self.debug = debug
        self.controller = controller
        self.default_location = default_location or controller.location
        self.location_type = location_type
        self.hardware_models = {}
        if self.debug:
            self.logger.setLevel(logging.DEBUG)
        else:
            self.logger.setLevel(logging.INFO)
        with open(path.join(path.dirname(__file__), "hardware_models.csv"), encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for record in reader:
                self.hardware_models[record["model"]] = record

        super().run(dryrun=self.dryrun, *args, **kwargs)


register_jobs(UnifiDataSource)
