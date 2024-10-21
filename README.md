# spcbridge
## Prerequisites
- Vanderbilt SPC panel, firmware version >= 3.8.5
- [SPC Bridge Generic Lite](https://www.lundix.se/spc-bridge-generic-lite/) or [SPC Bridge Generic](https://www.lundix.se/spc-bridge-generic/) from Lundix IT. **Please note!** The software module SPC Web Gateway isn't supported.
- Home Assistant system, Core version >= 2024.9.0, Frontend version >= 20240809.0

## Introduction
Integrating your security system with Home Assistant (HA) can significantly enhance the functionality and convenience of your home automation. By using the motion detectors to control your lights and window sensors to control your HVAC system you can help maintain an ideal temperature and save money on your energy bills. You can also switch off all lights and close the water valve when you arm the security system and leave your home. This not only provides added security but also helps prevent damage in case of emergencies.

By using this custom integration for HA, you can access all states and status from your SPC security system and even arm/disarm the system, bypass zones, and control SPC outputs and doors. However, it's important to note that the allowed commands are determined by the settings in the SPC panel.

To integrate your security system with HA, you will need the SPC Bridge Generic (Lite) from Lundix IT. The communication is based on Vanderbilt's official protocol FlexC and is completely local on your own network, ensuring your data and safety.

The SPC Bridge HA integration consists of following parts:
- SPC Bridge component (spcbridge): a HA custom component.
- SPC Bridge library (pyspcbridge): a python library for interacting with the SPC Bridge REST/Websocket API.
- SPC Bridge Card (spcbridge-card): a HA custom card to controlling the SPC alarm system.  

### Features
- Support for SPC areas, zones, outputs (mapping gates or virtual zones) and doors
- Encrypted local communication with the SPC Bridge
- Keypad controlled commands
- Allows the alarm detectors to be used for advanced automations in HA
- Support for multiple SPC systems (however a SPC Bridge is required for each SPC system)

## Installation
1. Download the latest release as a zip file and extract it into the `custom_components` folder in your HA installation.
2. Restart HA to load the integration into HA.
3. Go to Configuration -> Integrations and click the big orange '+' button. Look for SPC Bridge and click to add it.
4. Follow the configuration instructions.
5. The SPC Bridge integration is ready for use.
