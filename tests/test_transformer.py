"""Unit tests for transformer.py module."""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from oig_cloud_mcp.transformer import (
    transform_get_stats,
    _create_data_point,
    _transform_solar,
    _transform_battery,
    _transform_household,
)


class TestCreateDataPoint:
    """Tests for _create_data_point helper function."""

    def test_with_valid_float_kw(self) -> None:
        result = _create_data_point(1.23456, "kW", "Test description")
        assert result["value"] == 1.235
        assert result["unit"] == "kW"
        assert result["description"] == "Test description"

    def test_with_valid_percentage(self) -> None:
        result = _create_data_point(89, "%", "Battery level")
        assert result["value"] == 89
        assert result["unit"] == "%"
        assert result["description"] == "Battery level"

    def test_with_none_value_kw(self) -> None:
        result = _create_data_point(None, "kW", "Test")
        assert result["value"] == 0.0
        assert result["unit"] == "kW"

    def test_with_none_value_percentage(self) -> None:
        result = _create_data_point(None, "%", "Test")
        assert result["value"] == 0
        assert result["unit"] == "%"


class TestTransformSolar:
    """Tests for _transform_solar function."""

    def test_with_valid_data(self) -> None:
        actual_data = {"fv_p1": 3000, "fv_p2": 2500}
        result = _transform_solar(actual_data)

        assert "string_1" in result
        assert "string_2" in result
        assert "total" in result

        assert result["string_1"]["value"] == 3.0
        assert result["string_1"]["unit"] == "kW"
        assert result["string_2"]["value"] == 2.5
        assert result["total"]["value"] == 5.5

    def test_with_missing_keys(self) -> None:
        actual_data = {}
        result = _transform_solar(actual_data)

        assert result["string_1"]["value"] == 0.0
        assert result["string_2"]["value"] == 0.0
        assert result["total"]["value"] == 0.0

    def test_with_invalid_values(self) -> None:
        actual_data = {"fv_p1": "invalid", "fv_p2": None}
        result = _transform_solar(actual_data)

        assert result["string_1"]["value"] == 0.0
        assert result["string_2"]["value"] == 0.0


class TestTransformBattery:
    """Tests for _transform_battery function."""

    def test_with_valid_data(self) -> None:
        actual_data = {"bat_c": 85, "bat_p": -500}
        result = _transform_battery(actual_data)

        assert result["state_of_charge"]["value"] == 85
        assert result["state_of_charge"]["unit"] == "%"
        assert result["power_flow"]["value"] == -0.5
        assert result["power_flow"]["unit"] == "kW"

    def test_with_missing_keys(self) -> None:
        actual_data = {}
        result = _transform_battery(actual_data)

        assert result["state_of_charge"]["value"] == 0
        assert result["power_flow"]["value"] == 0.0


class TestTransformHousehold:
    """Tests for _transform_household function."""

    def test_with_valid_data(self) -> None:
        actual_data = {"aco_p": 1500}
        result = _transform_household(actual_data)

        assert result["total_load"]["value"] == 1.5
        assert result["total_load"]["unit"] == "kW"

    def test_with_missing_keys(self) -> None:
        actual_data = {}
        result = _transform_household(actual_data)

        assert result["total_load"]["value"] == 0.0


class TestTransformGetStats:
    """Tests for the main transform_get_stats function."""

    def test_with_complete_sample_response(self) -> None:
        sample_path: Path = Path(__file__).parent / "fixtures" / "sample-response.json"
        with open(sample_path, "r") as f:
            sample_data: Dict[str, Any] = json.load(f)

        result: Dict[str, Any] = transform_get_stats(sample_data)

        assert "solar_production" in result
        assert "battery" in result
        assert "household" in result

        assert "string_1" in result["solar_production"]
        assert "string_2" in result["solar_production"]
        assert "total" in result["solar_production"]

        assert "state_of_charge" in result["battery"]
        assert "power_flow" in result["battery"]

        assert "total_load" in result["household"]

        assert result["battery"]["state_of_charge"]["value"] == 89
        assert result["household"]["total_load"]["value"] == 0.253

    def test_with_empty_dict(self) -> None:
        result: Dict[str, Any] = transform_get_stats({})
        assert result == {}

    def test_with_none(self) -> None:
        result: Dict[str, Any] = transform_get_stats(None)
        assert result == {}

    def test_with_malformed_input_missing_actual(self) -> None:
        malformed: Dict[str, Any] = {"2205232120": {"actual": {}}}
        result: Dict[str, Any] = transform_get_stats(malformed)

        assert "solar_production" in result
        assert "battery" in result
        assert "household" in result

        assert result["solar_production"]["total"]["value"] == 0.0
        assert result["battery"]["state_of_charge"]["value"] == 0

    def test_with_empty_device_object(self) -> None:
        malformed: Dict[str, Any] = {"2205232120": {}}
        result: Dict[str, Any] = transform_get_stats(malformed)

        # Empty device object returns empty dict
        assert result == {}

    def test_with_malformed_input_no_device(self) -> None:
        malformed: Dict[str, Any] = {"2205232120": None}
        result: Dict[str, Any] = transform_get_stats(malformed)
        assert result == {}
