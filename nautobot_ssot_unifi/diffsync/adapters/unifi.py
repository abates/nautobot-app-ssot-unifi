"""Nautobot Ssot Unifi Adapter for Unifi SSoT app."""

from diffsync import DiffSync
from nautobot_ssot_unifi.diffsync.models.unifi import UnifiDevice


class UnifiAdapter(DiffSync):
    """DiffSync adapter for Unifi."""

    device = UnifiDevice

    top_level = ["device"]

    def __init__(self, *args, job=None, sync=None, client=None, **kwargs):
        """Initialize Unifi.

        Args:
            job (object, optional): Unifi job. Defaults to None.
            sync (object, optional): Unifi DiffSync. Defaults to None.
            client (object): Unifi API client connection object.
        """
        super().__init__(*args, **kwargs)
        self.job = job
        self.sync = sync
        self.conn = client

    def load(self):
        """Load data from Unifi into DiffSync models."""
        raise NotImplementedError
