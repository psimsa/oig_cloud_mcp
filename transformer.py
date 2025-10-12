"""Data transformation utilities for OIG Cloud MCP.

This module converts the raw JSON returned by the OIG Cloud API into a
compact, self-describing format that is friendly for AI consumption.

Public API
- transform_get_stats(raw_data: dict) -> dict
    Converts the raw response from client.get_stats() into the
    structured mapping defined in data_mapping_spec.md.
"""

from typing import Any, Dict, Union


def _create_data_point(value: Any, unit: str, description: str) -> Dict[str, Any]:
    """Create a standardized data point dictionary.

    - Coerces numeric values into either int (for percentage) or float.
    - Rounds floating-point kW values to 3 decimal places for readability.
    """
    v: Union[int, float]
    if value is None:
        if unit == "%":
            v = 0
        else:
            v = 0.0
        return {"value": v, "unit": unit, "description": description}

    try:
        if unit == "%":
            v = int(value)
        else:
            v = float(value)
            # Round kW-style values to 3 decimal places to keep payloads tidy
            v = round(v, 3)
    except Exception:
        # Fall back to sensible defaults if coercion fails
        v = 0 if unit == "%" else 0.0

    return {"value": v, "unit": unit, "description": description}


def _transform_solar(actual_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Build the `solar_production` section from the 'actual' payload.

    Extracts fv_p1 and fv_p2 (watts), converts them to kW and returns
    the three keyed entries: string_1, string_2 and total.
    """
    fv_p1_w = actual_data.get("fv_p1", 0.0)
    fv_p2_w = actual_data.get("fv_p2", 0.0)

    # Safely coerce to numbers and convert from W -> kW
    try:
        fv_p1_kw = float(fv_p1_w) / 1000.0
    except Exception:
        fv_p1_kw = 0.0
    try:
        fv_p2_kw = float(fv_p2_w) / 1000.0
    except Exception:
        fv_p2_kw = 0.0

    total_kw = fv_p1_kw + fv_p2_kw

    return {
        "string_1": _create_data_point(
            fv_p1_kw,
            "kW",
            "Current power production from solar panel string 1.",
        ),
        "string_2": _create_data_point(
            fv_p2_kw,
            "kW",
            "Current power production from solar panel string 2.",
        ),
        "total": _create_data_point(
            total_kw,
            "kW",
            "Total current power production from all solar panels.",
        ),
    }


def _transform_battery(actual_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Build the `battery` section from the 'actual' payload.

    - state_of_charge is taken directly from bat_c and expressed as percentage.
    - power_flow is taken from bat_p (watts) and converted to kW.
    """
    soc = actual_data.get("bat_c", 0)
    bat_p_w = actual_data.get("bat_p", 0.0)

    try:
        bat_p_kw = float(bat_p_w) / 1000.0
    except Exception:
        bat_p_kw = 0.0

    return {
        "state_of_charge": _create_data_point(
            soc,
            "%",
            "Current charge level of the battery.",
        ),
        "power_flow": _create_data_point(
            bat_p_kw,
            "kW",
            "Current battery power flow. Positive values indicate charging, negative values indicate discharging.",
        ),
    }


def _transform_household(actual_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Build the `household` section from the 'actual' payload.

    - total_load is taken from aco_p (watts) and converted to kW.
    """
    aco_p_w = actual_data.get("aco_p", 0.0)
    try:
        aco_p_kw = float(aco_p_w) / 1000.0
    except Exception:
        aco_p_kw = 0.0

    return {
        "total_load": _create_data_point(
            aco_p_kw,
            "kW",
            "Total current electricity consumption of the household.",
        )
    }


def transform_get_stats(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """Transform raw get_stats() output into the AI-friendly schema.

    - Handles None or empty inputs gracefully.
    - Extracts the first device entry from the top-level dict (device id keyed)
      and uses its "actual" sub-tree as the source of truth.
    """
    if not raw_data:
        return {}

    # The API response is keyed by device id. Use the first device object.
    device_obj: Dict[str, Any] = next(iter(raw_data.values()), {})
    if not device_obj:
        return {}

    actual = device_obj.get("actual", {}) or {}

    solar = _transform_solar(actual)
    battery = _transform_battery(actual)
    household = _transform_household(actual)

    return {
        "solar_production": solar,
        "battery": battery,
        "household": household,
    }


if __name__ == "__main__":
    # Quick local smoke-test when running the module directly.
    import json
    import pathlib

    sample = pathlib.Path(__file__).parent / "sample-response.json"
    if sample.exists():
        data = json.loads(sample.read_text())
        print(json.dumps(transform_get_stats(data), indent=2))
    else:
        print("No sample-response.json found in project root for quick test.")
