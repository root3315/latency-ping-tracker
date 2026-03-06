#!/usr/bin/env python3
"""
Unit tests for Latency Ping Tracker
"""

import unittest
import json
import os
import subprocess
import tempfile
import statistics
from datetime import datetime
from unittest.mock import patch, MagicMock
from io import StringIO

from latency_tracker import (
    ping_host,
    load_data,
    save_data,
    record_latency,
    get_statistics,
    list_hosts,
    clear_host_data,
    clear_all_data,
    export_csv,
)


class TestPingHost(unittest.TestCase):
    """Tests for ping_host function."""

    @patch("latency_tracker.subprocess.run")
    def test_ping_success(self, mock_run):
        """Test successful ping response."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="PING google.com (142.250.80.46) 56(84) bytes of data.\n"
            "64 bytes from lga34s33-in-f14.1e100.net (142.250.80.46): icmp_seq=1 ttl=117 time=23.4 ms\n"
        )
        latency = ping_host("google.com")
        self.assertEqual(latency, 23.4)

    @patch("latency_tracker.subprocess.run")
    def test_ping_success_with_float_time(self, mock_run):
        """Test ping with decimal milliseconds."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="64 bytes from 8.8.8.8: icmp_seq=1 ttl=118 time=12.567 ms\n"
        )
        latency = ping_host("8.8.8.8")
        self.assertEqual(latency, 12.567)

    @patch("latency_tracker.subprocess.run")
    def test_ping_failure_nonzero_returncode(self, mock_run):
        """Test ping with non-zero return code."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout=""
        )
        latency = ping_host("invalid.host")
        self.assertIsNone(latency)

    @patch("latency_tracker.subprocess.run")
    def test_ping_no_time_in_output(self, mock_run):
        """Test ping output without time= field."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="PING google.com (142.250.80.46) 56(84) bytes of data.\n"
        )
        latency = ping_host("google.com")
        self.assertIsNone(latency)

    @patch("latency_tracker.subprocess.run")
    def test_ping_timeout_expired(self, mock_run):
        """Test ping that times out."""
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="ping", timeout=7)
        latency = ping_host("slow.host")
        self.assertIsNone(latency)

    @patch("latency_tracker.subprocess.run")
    def test_ping_value_error(self, mock_run):
        """Test ping with malformed time value."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="64 bytes from host: icmp_seq=1 ttl=118 time=invalid ms\n"
        )
        latency = ping_host("host")
        self.assertIsNone(latency)


class TestDataPersistence(unittest.TestCase):
    """Tests for data loading and saving functions."""

    def setUp(self):
        """Create temporary directory for test data."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)

    def tearDown(self):
        """Clean up temporary directory."""
        os.chdir(self.original_cwd)
        for f in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, f))
        os.rmdir(self.temp_dir)

    def test_load_data_empty(self):
        """Test loading data when no file exists."""
        data = load_data()
        self.assertEqual(data, {"hosts": {}})

    def test_load_data_existing(self):
        """Test loading existing data file."""
        test_data = {
            "hosts": {
                "google.com": {
                    "measurements": [{"timestamp": "2024-01-01T00:00:00", "latency_ms": 25.0}]
                }
            }
        }
        with open("latency_data.json", "w") as f:
            json.dump(test_data, f)

        data = load_data()
        self.assertEqual(data, test_data)

    def test_save_data(self):
        """Test saving data to file."""
        test_data = {
            "hosts": {
                "example.com": {
                    "measurements": [{"timestamp": "2024-01-01T00:00:00", "latency_ms": 30.5}]
                }
            }
        }
        save_data(test_data)

        with open("latency_data.json", "r") as f:
            loaded = json.load(f)

        self.assertEqual(loaded, test_data)

    def test_save_data_overwrites(self):
        """Test that save_data overwrites existing file."""
        initial_data = {"hosts": {"old.com": {"measurements": []}}}
        save_data(initial_data)

        new_data = {"hosts": {"new.com": {"measurements": []}}}
        save_data(new_data)

        with open("latency_data.json", "r") as f:
            loaded = json.load(f)

        self.assertEqual(loaded, new_data)


class TestRecordLatency(unittest.TestCase):
    """Tests for record_latency function."""

    def setUp(self):
        """Create temporary directory for test data."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)

    def tearDown(self):
        """Clean up temporary directory."""
        os.chdir(self.original_cwd)
        for f in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, f))
        os.rmdir(self.temp_dir)

    def test_record_latency_new_host(self):
        """Test recording latency for a new host."""
        record_latency("newhost.com", 45.0)
        data = load_data()

        self.assertIn("newhost.com", data["hosts"])
        self.assertEqual(len(data["hosts"]["newhost.com"]["measurements"]), 1)
        self.assertEqual(
            data["hosts"]["newhost.com"]["measurements"][0]["latency_ms"], 45.0
        )
        self.assertIn("created_at", data["hosts"]["newhost.com"])

    def test_record_latency_existing_host(self):
        """Test recording multiple measurements for same host."""
        record_latency("existing.com", 20.0)
        record_latency("existing.com", 25.0)
        record_latency("existing.com", 30.0)

        data = load_data()
        measurements = data["hosts"]["existing.com"]["measurements"]

        self.assertEqual(len(measurements), 3)
        self.assertEqual(measurements[0]["latency_ms"], 20.0)
        self.assertEqual(measurements[1]["latency_ms"], 25.0)
        self.assertEqual(measurements[2]["latency_ms"], 30.0)

    def test_record_latency_timestamp_format(self):
        """Test that timestamps are in ISO format."""
        record_latency("host.com", 50.0)
        data = load_data()

        timestamp = data["hosts"]["host.com"]["measurements"][0]["timestamp"]
        datetime.fromisoformat(timestamp)


class TestGetStatistics(unittest.TestCase):
    """Tests for get_statistics function."""

    def setUp(self):
        """Create temporary directory for test data."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)

    def tearDown(self):
        """Clean up temporary directory."""
        os.chdir(self.original_cwd)
        for f in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, f))
        os.rmdir(self.temp_dir)

    def test_get_statistics_unknown_host(self):
        """Test statistics for unknown host."""
        stats = get_statistics("unknown.com")
        self.assertIsNone(stats)

    def test_get_statistics_empty_measurements(self):
        """Test statistics when host has no measurements."""
        data = {"hosts": {"empty.com": {"measurements": []}}}
        save_data(data)

        stats = get_statistics("empty.com")
        self.assertIsNone(stats)

    def test_get_statistics_single_measurement(self):
        """Test statistics with single measurement."""
        record_latency("single.com", 100.0)
        stats = get_statistics("single.com")

        self.assertEqual(stats["count"], 1)
        self.assertEqual(stats["min"], 100.0)
        self.assertEqual(stats["max"], 100.0)
        self.assertEqual(stats["avg"], 100.0)
        self.assertEqual(stats["median"], 100.0)
        self.assertEqual(stats["stdev"], 0.0)
        self.assertEqual(stats["last"], 100.0)

    def test_get_statistics_multiple_measurements(self):
        """Test statistics with multiple measurements."""
        latencies = [10.0, 20.0, 30.0, 40.0, 50.0]
        for lat in latencies:
            record_latency("multi.com", lat)

        stats = get_statistics("multi.com")

        self.assertEqual(stats["count"], 5)
        self.assertEqual(stats["min"], 10.0)
        self.assertEqual(stats["max"], 50.0)
        self.assertEqual(stats["avg"], 30.0)
        self.assertEqual(stats["median"], 30.0)
        self.assertGreater(stats["stdev"], 0)
        self.assertEqual(stats["last"], 50.0)

    def test_get_statistics_calculations(self):
        """Test that statistical calculations are correct."""
        latencies = [5.0, 10.0, 15.0]
        for lat in latencies:
            record_latency("calc.com", lat)

        stats = get_statistics("calc.com")

        expected_avg = statistics.mean(latencies)
        expected_median = statistics.median(latencies)
        expected_stdev = statistics.stdev(latencies)

        self.assertAlmostEqual(stats["avg"], expected_avg)
        self.assertAlmostEqual(stats["median"], expected_median)
        self.assertAlmostEqual(stats["stdev"], expected_stdev)


class TestListHosts(unittest.TestCase):
    """Tests for list_hosts function."""

    def setUp(self):
        """Create temporary directory for test data."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)

    def tearDown(self):
        """Clean up temporary directory."""
        os.chdir(self.original_cwd)
        for f in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, f))
        os.rmdir(self.temp_dir)

    def test_list_hosts_empty(self):
        """Test listing hosts when none exist."""
        hosts = list_hosts()
        self.assertEqual(hosts, [])

    def test_list_hosts_with_data(self):
        """Test listing hosts with data present."""
        record_latency("host1.com", 10.0)
        record_latency("host2.com", 20.0)
        record_latency("host3.com", 30.0)

        hosts = list_hosts()

        self.assertEqual(len(hosts), 3)
        self.assertIn("host1.com", hosts)
        self.assertIn("host2.com", hosts)
        self.assertIn("host3.com", hosts)


class TestClearHostData(unittest.TestCase):
    """Tests for clear_host_data function."""

    def setUp(self):
        """Create temporary directory for test data."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)

    def tearDown(self):
        """Clean up temporary directory."""
        os.chdir(self.original_cwd)
        for f in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, f))
        os.rmdir(self.temp_dir)

    def test_clear_host_data_existing_host(self):
        """Test clearing data for existing host."""
        record_latency("toclear.com", 100.0)
        record_latency("toclear.com", 200.0)

        result = clear_host_data("toclear.com")

        self.assertTrue(result)
        data = load_data()
        self.assertNotIn("toclear.com", data["hosts"])

    def test_clear_host_data_unknown_host(self):
        """Test clearing data for unknown host."""
        result = clear_host_data("unknown.com")
        self.assertFalse(result)

    def test_clear_host_data_preserves_other_hosts(self):
        """Test that clearing one host preserves others."""
        record_latency("keep.com", 50.0)
        record_latency("remove.com", 100.0)

        clear_host_data("remove.com")

        data = load_data()
        self.assertIn("keep.com", data["hosts"])
        self.assertNotIn("remove.com", data["hosts"])


class TestClearAllData(unittest.TestCase):
    """Tests for clear_all_data function."""

    def setUp(self):
        """Create temporary directory for test data."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)

    def tearDown(self):
        """Clean up temporary directory."""
        os.chdir(self.original_cwd)
        for f in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, f))
        os.rmdir(self.temp_dir)

    def test_clear_all_data(self):
        """Test clearing all data."""
        record_latency("host1.com", 10.0)
        record_latency("host2.com", 20.0)

        clear_all_data()

        data = load_data()
        self.assertEqual(data, {"hosts": {}})


class TestExportCSV(unittest.TestCase):
    """Tests for export_csv function."""

    def setUp(self):
        """Create temporary directory for test data."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)

    def tearDown(self):
        """Clean up temporary directory."""
        os.chdir(self.original_cwd)
        for f in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, f))
        os.rmdir(self.temp_dir)

    def test_export_csv_unknown_host(self):
        """Test exporting CSV for unknown host."""
        filename = export_csv("unknown.com")
        self.assertEqual(filename, "")

    def test_export_csv_creates_file(self):
        """Test that export_csv creates a file."""
        record_latency("export.com", 25.0)
        record_latency("export.com", 30.0)

        filename = export_csv("export.com")

        self.assertEqual(filename, "export_com_latency.csv")
        self.assertTrue(os.path.exists(filename))

    def test_export_csv_content(self):
        """Test CSV file content format."""
        record_latency("test.com", 42.5)
        record_latency("test.com", 55.5)

        filename = export_csv("test.com")

        with open(filename, "r") as f:
            lines = f.read().strip().split("\n")

        self.assertEqual(lines[0], "timestamp,latency_ms")
        self.assertEqual(len(lines), 3)

    def test_export_csv_filename_format(self):
        """Test that filename replaces dots with underscores."""
        record_latency("sub.domain.example.com", 100.0)

        filename = export_csv("sub.domain.example.com")

        self.assertEqual(filename, "sub_domain_example_com_latency.csv")


if __name__ == "__main__":
    unittest.main()
