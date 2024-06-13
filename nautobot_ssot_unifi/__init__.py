"""App declaration for nautobot_ssot_unifi."""
# Metadata is inherited from Nautobot. If not including Nautobot in the environment, this should be added
from importlib import metadata

from nautobot.apps import NautobotAppConfig

__version__ = metadata.version(__name__)


class NautobotSSOTUnifiConfig(NautobotAppConfig):
    """App configuration for the nautobot_ssot_unifi app."""

    name = "nautobot_ssot_unifi"
    verbose_name = "Nautobot Ssot Unifi"
    version = __version__
    author = "Andrew Bates"
    description = "Nautobot SSoT integration for Ubiquiti Unifi.."
    base_url = "ssot-unifi"
    required_settings = []
    min_version = "2.0.0"
    max_version = "2.9999"
    default_settings = {}
    caching_config = {}


config = NautobotSSOTUnifiConfig  # pylint:disable=invalid-name
