"""Jobs for Unifi SSoT integration."""


from nautobot.apps.jobs import BooleanVar, register_jobs
from nautobot_ssot.jobs.base import DataSource, DataTarget

from nautobot_ssot_unifi.diffsync.adapters import unifi, nautobot


name = "Unifi SSoT"  # pylint: disable=invalid-name


class UnifiDataSource(DataSource):
    """Unifi SSoT Data Source."""

    debug = BooleanVar(description="Enable for more verbose debug logging", default=False)

    class Meta:  # pylint: disable=too-few-public-methods
        """Meta data for Unifi."""

        name = "Unifi to Nautobot"
        data_source = "Unifi"
        data_target = "Nautobot"
        description = "Sync information from Unifi to Nautobot"

    @classmethod
    def config_information(cls):
        """Dictionary describing the configuration of this DataSource."""
        return {}

    @classmethod
    def data_mappings(cls):
        """List describing the data mappings involved in this DataSource."""
        return ()

    def load_source_adapter(self):
        """Load data from Unifi into DiffSync models."""
        self.source_adapter = unifi.UnifiAdapter(job=self, sync=self.sync)
        self.source_adapter.load()

    def load_target_adapter(self):
        """Load data from Nautobot into DiffSync models."""
        self.target_adapter = nautobot.NautobotAdapter(job=self, sync=self.sync)
        self.target_adapter.load()

    def run(self, dryrun, memory_profiling, debug, *args, **kwargs):  # pylint: disable=arguments-differ
        """Perform data synchronization."""
        self.debug = debug
        self.dryrun = dryrun
        self.memory_profiling = memory_profiling
        super().run(dryrun=self.dryrun, memory_profiling=self.memory_profiling, *args, **kwargs)


class UnifiDataTarget(DataTarget):
    """Unifi SSoT Data Target."""

    debug = BooleanVar(description="Enable for more verbose debug logging", default=False)

    class Meta:  # pylint: disable=too-few-public-methods
        """Meta data for Unifi."""

        name = "Nautobot to Unifi"
        data_source = "Nautobot"
        data_target = "Unifi"
        description = "Sync information from Nautobot to Unifi"

    @classmethod
    def config_information(cls):
        """Dictionary describing the configuration of this DataTarget."""
        return {}

    @classmethod
    def data_mappings(cls):
        """List describing the data mappings involved in this DataSource."""
        return ()

    def load_source_adapter(self):
        """Load data from Nautobot into DiffSync models."""
        self.source_adapter = nautobot.NautobotAdapter(job=self, sync=self.sync)
        self.source_adapter.load()

    def load_target_adapter(self):
        """Load data from Unifi into DiffSync models."""
        self.target_adapter = unifi.UnifiAdapter(job=self, sync=self.sync)
        self.target_adapter.load()

    def run(self, dryrun, memory_profiling, debug, *args, **kwargs):  # pylint: disable=arguments-differ
        """Perform data synchronization."""
        self.debug = debug
        self.dryrun = dryrun
        self.memory_profiling = memory_profiling
        super().run(dryrun=self.dryrun, memory_profiling=self.memory_profiling, *args, **kwargs)


jobs = [UnifiDataSource, UnifiDataTarget]
register_jobs(*jobs)
