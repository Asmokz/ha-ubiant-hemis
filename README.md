# Ubiant Hemis (Flexom) – Home Assistant Integration

Custom Home Assistant integration for Ubiant / Flexom smart buildings.

## Features
- Sensors (temperature, battery, switches…)
- Covers (rollers / shutters)
- Lights (relay-based on/off)
- Heating (pilot wire – away / eco / comfort)
- Automatic token renewal (the renewed token is saved)
- Re-authentication from the UI if your password changes

## Installation (HACS)
1. Open HACS
2. Top-right menu (⋮) → **Custom repositories**
3. Add repository:
   - URL: `https://github.com/Asmokz/ha-ubiant-hemis`
   - Type: **Integration**
4. Search for "Ubiant Hemis (Flexom)" in HACS and download it
5. Restart Home Assistant
6. Settings → Devices & services → **Add integration** → "Ubiant Hemis"

Requires Home Assistant 2024.12 or newer.

## Manual installation
Copy the `custom_components/ubiant_hemis` folder into the `custom_components`
folder of your Home Assistant configuration, then restart Home Assistant.

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
This project is not affiliated with Ubiant or Flexom and is a beta that was not tested on multiple configurations.
A lot of works have been done with the help of ChatGPT so don't hesitate to modify and notify for any improvements.
As Flexom is no longer maintained, the solution provided here will likely be static and not updated, new features will come with personal needs.

## License
MIT, see [LICENSE](LICENSE).
