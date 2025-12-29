# Ubiant Hemis (Flexom) – Home Assistant Integration

Custom Home Assistant integration for Ubiant / Flexom smart buildings.

## Features
- Sensors (temperature, battery, switches…)
- Covers (rollers / shutters)
- Lights (relay-based on/off)
- Heating (pilot wire – away / eco / comfort)
- Automatic token renewal

## Installation (HACS)
1. Open HACS
2. Integrations → Custom repositories
3. Add repository:
   - URL: https://github.com/Asmokz/ha-ubiant-hemis
   - Category: Integration
4. Install "Ubiant Hemis"
5. Restart Home Assistant

## Configuration
- Email
- Password

The integration automatically discovers:
- Building ID
- Hemis API base URL

## Supported devices
- UBIWIZZ relay modules
- Vertical rollers
- Pilot wire heaters (3 modes)

## Disclaimer
This project is not affiliated with Ubiant or Flexom and is a beta that is not tested on multiple configurations.
