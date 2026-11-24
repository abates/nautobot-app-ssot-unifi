"""Verify that the adapter routes requests by the UniFi site name."""

import logging
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import AsyncMock, patch

from aiounifi.models.site import Site

from nautobot_ssot_unifi.ssot.adapters import UnifiAdapter


class SiteRoutingTests(TestCase):
    """Verify legacy and Network 11 site responses."""

    def test_selects_each_site_by_name(self):
        """Site ID format does not affect the route for a device request."""
        sites = [
            Site({"name": "default", "_id": "0123456789abcdef01234567"}),
            Site(
                {
                    "name": "workshop",
                    "_id": "11111111-1111-4111-8111-111111111111",
                    "legacy_id": "123456789abcdef012345678",
                }
            ),
        ]
        client = SimpleNamespace(current_site="default", get_sites=AsyncMock(return_value=sites))
        selected = []

        async def get_devices():
            selected.append(client.current_site)
            return []

        client.get_devices = get_devices
        job = SimpleNamespace(controller=SimpleNamespace(name="Controller"), logger=logging.getLogger(__name__))
        adapter = UnifiAdapter(
            job=job, controller_name="Controller", default_location_type="Site", default_location_name="Home"
        )
        with patch("nautobot_ssot_unifi.ssot.adapters.Client", return_value=client):
            adapter.load(
                host="controller.example",
                port=443,
                username="reader",
                password="test-only",
                verify_cert=True,
                timeout=1,
            )
        self.assertEqual(selected, ["default", "workshop"])
