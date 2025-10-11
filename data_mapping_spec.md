OIG Cloud MCP - AI-Friendly Data Mapping Specification
======================================================

1\. Objective
-------------

To transform the raw, cryptic JSON response from the OIG Cloud API into a structured, self-describing, and human-readable format. This new format is designed to be directly interpretable by Large Language Models (LLMs) and AI agents, enabling them to easily understand and reason about the state of a user's photovoltaic (PV) system.

2\. Implementation Overview
---------------------------

A new Python module, `transformer.py`, will be created. This module will contain a primary function, `transform_get_stats(raw_data: dict) -> dict`.

This function will be called by the `get_basic_data` tool in `tools.py` immediately after receiving a successful response from the OIG Cloud API. The original raw data will be replaced with the new, transformed data in the tool's final output.

The transformation will be based on the mappings discovered in the official OIG Cloud Home Assistant integration's sensor definitions.

3\. Data Mapping for `get_basic_data`
-------------------------------------

The `transform_get_stats` function will process the raw data from the `get_stats()` API call and produce a JSON object with the following structure. All power values will be converted from Watts (W) to Kilowatts (kW) for better readability by AI agents.

### 3.1. Top-Level Structure

The output will be a dictionary with three main keys: `solar_production`, `battery`, and `household`.

    {
      "solar_production": { ... },
      "battery": { ... },
      "household": { ... }
    }
    

### 3.2. `solar_production` Object

This object describes the real-time power generation from the solar panels.

**AI-Friendly Key**

**Source Path (from raw JSON)**

**Unit**

**Conversion**

**Description**

`string_1`

`actual.fv_p1`

kW

Divide by 1000

Current power production from solar panel string 1.

`string_2`

`actual.fv_p2`

kW

Divide by 1000

Current power production from solar panel string 2.

`total`

`actual.fv_p1` + `actual.fv_p2`

kW

Sum and divide by 1000

Total current power production from all solar panels.

**Example JSON Structure:**

    "solar_production": {
      "string_1": { "value": 1.5, "unit": "kW", "description": "..." },
      "string_2": { "value": 2.1, "unit": "kW", "description": "..." },
      "total":    { "value": 3.6, "unit": "kW", "description": "..." }
    }
    

### 3.3. `battery` Object

This object describes the current status and power flow of the battery system.

**AI-Friendly Key**

**Source Path (from raw JSON)**

**Unit**

**Conversion**

**Description**

`state_of_charge`

`actual.bat_c`

%

None

Current charge level of the battery.

`power_flow`

`actual.bat_p`

kW

Divide by 1000

Current battery power flow. Positive values indicate charging, negative values indicate discharging.

**Example JSON Structure:**

    "battery": {
      "state_of_charge": { "value": 89, "unit": "%", "description": "..." },
      "power_flow":      { "value": -0.467, "unit": "kW", "description": "..." }
    }
    

### 3.4. `household` Object

This object describes the home's electricity consumption.

**AI-Friendly Key**

**Source Path (from raw JSON)**

**Unit**

**Conversion**

**Description**

`total_load`

`actual.aco_p`

kW

Divide by 1000

Total current electricity consumption of the household.

**Example JSON Structure:**

    "household": {
      "total_load": { "value": 0.253, "unit": "kW", "description": "..." }
    }
    

4\. Future Expansion
--------------------

This specification currently only covers the `get_basic_data` tool. Similar transformation layers can be designed for `get_extended_data` and `get_notifications` in the future to make historical data and system alerts equally accessible to AI agents.