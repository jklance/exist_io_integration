"""Tests for sync orchestration."""

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest

from exist_backup import db
from exist_backup.sync import run_sync


@pytest.fixture
def sync_config(tmp_path):
    return {
        "auth": {"token": "test-token"},
        "sync": {"database": str(tmp_path / "test.db")},
        "export": {"output_dir": str(tmp_path / "export"), "template": "daily"},
    }


@pytest.fixture
def mock_client(sample_profile, sample_attributes):
    """Mock ExistClient that returns sample data (for full sync)."""
    client = MagicMock()
    client.get_profile.return_value = sample_profile
    client.get_attributes.return_value = sample_attributes

    def fake_values(attr_name, date_max=None):
        return iter([
            {"date": "2024-12-01", "value": "100"},
            {"date": "2024-12-02", "value": "200"},
        ])

    client.get_attribute_values.side_effect = fake_values
    return client


def _make_incremental_client(sample_profile, sample_attributes, value_date):
    """Build a mock client that returns bulk with-values data."""
    client = MagicMock()
    client.get_profile.return_value = sample_profile

    def fake_with_values(days=1, date_max=None):
        for attr in sample_attributes:
            result = dict(attr)
            result["values"] = [{"date": str(value_date), "value": "42"}]
            yield result

    client.get_attributes_with_values.side_effect = fake_with_values
    return client


class TestRunSync:
    @patch("exist_backup.sync.api.ExistClient")
    def test_full_sync(self, MockClient, sync_config, mock_client, sample_attributes):
        MockClient.return_value = mock_client

        result = run_sync(sync_config, full=True)

        assert result["status"] == "success"
        assert result["attributes_synced"] == len(sample_attributes)
        assert result["values_synced"] > 0
        assert result["errors"] == []

        # Verify data in database
        conn = db.connect(sync_config["sync"]["database"])
        profile = db.get_profile(conn)
        assert profile["username"] == "testuser"

        stats = db.get_sync_status(conn)
        assert stats["total_attributes"] == len(sample_attributes)
        assert stats["total_values"] > 0
        conn.close()

    @patch("exist_backup.sync.api.ExistClient")
    def test_incremental_sync_uses_bulk_endpoint(
        self, MockClient, sync_config, sample_profile, sample_attributes
    ):
        yesterday = date.today() - timedelta(days=1)
        client = _make_incremental_client(sample_profile, sample_attributes, yesterday)
        MockClient.return_value = client

        result = run_sync(sync_config, full=False)

        assert result["status"] == "success"
        assert result["attributes_synced"] == len(sample_attributes)
        assert result["values_synced"] == len(sample_attributes)  # 1 value each
        assert result["errors"] == []

        # Should NOT have called per-attribute endpoints
        client.get_attributes.assert_not_called()
        client.get_attribute_values.assert_not_called()
        # Should have called bulk endpoint
        client.get_attributes_with_values.assert_called_once()

    @patch("exist_backup.sync.api.ExistClient")
    def test_incremental_sync_skips_already_synced_values(
        self, MockClient, sync_config, sample_profile, sample_attributes
    ):
        yesterday = date.today() - timedelta(days=1)
        client = _make_incremental_client(sample_profile, sample_attributes, yesterday)
        MockClient.return_value = client

        # First sync populates data
        run_sync(sync_config, full=False)

        # Second sync — same data, should find nothing new
        client2 = _make_incremental_client(sample_profile, sample_attributes, yesterday)
        MockClient.return_value = client2
        result = run_sync(sync_config, full=False)

        assert result["status"] == "success"
        assert result["values_synced"] == 0

    @patch("exist_backup.sync.api.ExistClient")
    def test_incremental_sync_handles_attribute_error(
        self, MockClient, sync_config, sample_profile, sample_attributes
    ):
        client = MagicMock()
        client.get_profile.return_value = sample_profile

        def failing_with_values(days=1, date_max=None):
            # First attribute succeeds, rest raise
            first = dict(sample_attributes[0])
            first["values"] = [{"date": "2024-12-01", "value": "42"}]
            yield first
            raise Exception("API error")

        client.get_attributes_with_values.side_effect = failing_with_values
        MockClient.return_value = client

        result = run_sync(sync_config, full=False)

        assert result["status"] == "partial"
        assert result["attributes_synced"] == 1
        assert len(result["errors"]) > 0

    @patch("exist_backup.sync.api.ExistClient")
    def test_sync_no_token(self, MockClient, tmp_path):
        config = {
            "auth": {"token": ""},
            "sync": {"database": str(tmp_path / "test.db")},
        }
        with pytest.raises(SystemExit):
            run_sync(config)

    @patch("exist_backup.sync.api.ExistClient")
    def test_sync_handles_attribute_error(self, MockClient, sync_config, sample_profile, sample_attributes):
        client = MagicMock()
        client.get_profile.return_value = sample_profile
        client.get_attributes.return_value = sample_attributes
        client.get_attribute_values.side_effect = Exception("API error")
        MockClient.return_value = client

        result = run_sync(sync_config, full=True)

        assert result["status"] == "error"
        assert len(result["errors"]) == len(sample_attributes)
