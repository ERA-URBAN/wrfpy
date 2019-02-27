#!/usr/bin/env python

"""
description:    Configuration part of wrfpy
license:        APACHE 2.0
"""

import os
import tempfile
import unittest

import pkg_resources

from wrfpy.config import config


class TestConfig(unittest.TestCase):
    """Tests for the config module."""

    def test_load_valid_config(self):
        """Test validation for run_hours fields in general."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = os.path.join(temp_dir, "config.json")
            cfg = self._create_basic_config(config_file)
            cfg._check_config()
            self.assertEqual(1, cfg.config["options_general"]["boundary_interval"])

    def test_general_run_hours(self):
        """Test validation for run_hours fields in wps."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = os.path.join(temp_dir, "config.json")
            cfg = self._create_basic_config(config_file)

            # fail to validate if wps run_hours is not present
            cfg.config["options_general"]["run_hours"] = None
            with self.assertRaises(AssertionError):
                cfg._check_general()

    def test_wps_run_hours(self):
        """Test validation for run_hours fields in general and wps."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = os.path.join(temp_dir, "config.json")
            cfg = self._create_basic_config(config_file)

            # fail to validate if general run_hours is not present
            cfg.config["options_wps"]["run_hours"] = None
            with self.assertRaises(AssertionError):
                cfg._check_wps()

    def test_start_date_before_end_date_validation(self):
        """Test validation for start date coming before end date."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = os.path.join(temp_dir, "config.json")
            cfg = self._create_basic_config(config_file)

            # fail to validate if general run_hours is not present
            cfg.config["options_general"]["date_start"], \
            cfg.config["options_general"]["date_end"] = cfg.config["options_general"]["date_end"], \
                                                        cfg.config["options_general"]["date_start"]

            with self.assertRaises(IOError):
                cfg._check_general()

    @classmethod
    def _create_basic_config(cls, config_file: str) -> config:
        """Create minimal configuration file for unit config unit tests."""
        cfg = config(wrfpy_config=config_file)
        cfg._read_json()
        # general
        cfg.config["options_general"]["boundary_interval"] = 1
        cfg.config["options_general"]["date_end"] = "2019-01-01_01"
        cfg.config["options_general"]["date_start"] = "2019-01-01_00"
        cfg.config["options_general"]["run_hours"] = "1"
        # wps
        cfg.config["options_wps"]["namelist.wps"] = cls._get_example_namelist()
        cfg.config["options_wps"]["run_hours"] = "1"
        # wrf
        cfg.config["options_wrf"]["namelist.input"] = cls._get_example_namelist()
        return cfg

    @classmethod
    def _get_example_namelist(cls) -> str:
        resource_package = __name__
        resource_path = '/'.join(('..', 'wrfpy', 'examples', 'namelist.wps'))
        filename = pkg_resources.resource_filename(resource_package, resource_path)
        return os.path.realpath(filename)


if __name__ == '__main__':
    unittest.main()
