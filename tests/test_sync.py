"""Tests for sync orchestration."""

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
    """Mock ExistClient that returns sample data."""
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
