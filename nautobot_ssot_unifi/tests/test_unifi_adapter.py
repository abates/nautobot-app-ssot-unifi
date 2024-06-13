"""Test Unifi adapter."""

import json
import uuid
from unittest.mock import MagicMock

from django.contrib.contenttypes.models import ContentType
from nautobot.extras.models import Job, JobResult
from nautobot.core.testing import TransactionTestCase
from nautobot_ssot_unifi.diffsync.adapters.unifi import UnifiAdapter
from nautobot_ssot_unifi.jobs import UnifiDataSource


def load_json(path):
    """Load a json file."""
    with open(path, encoding="utf-8") as file:
        return json.loads(file.read())


DEVICE_FIXTURE = load_json("./nautobot_ssot_unifi/tests/fixtures/get_devices.json")


class TestUnifiAdapterTestCase(TransactionTestCase):
    """Test NautobotSSOTUnifiAdapter class."""

    databases = ("default", "job_logs")

    def setUp(self):  # pylint: disable=invalid-name
        """Initialize test case."""
        self.unifi_client = MagicMock()
        self.unifi_client.get_devices.return_value = DEVICE_FIXTURE

        self.job = UnifiDataSource()
        self.job.job_result = JobResult.objects.create(
            name=self.job.class_path, obj_type=ContentType.objects.get_for_model(Job), user=None, job_id=uuid.uuid4()
        )
        self.unifi = UnifiAdapter(job=self.job, sync=None, client=self.unifi_client)

    def test_data_loading(self):
        """Test Nautobot Ssot Unifi load() function."""
        # self.unifi.load()
        # self.assertEqual(
        #     {dev["name"] for dev in DEVICE_FIXTURE},
        #     {dev.get_unique_id() for dev in self.unifi.get_all("device")},
        # )
