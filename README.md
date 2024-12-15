# spcbridge
## Prerequisites
- Vanderbilt SPC panel, firmware version >= 3.8.5
- [SPC Bridge Generic Lite](https://www.lundix.se/spc-bridge-generic-lite/) or [SPC Bridge Generic](https://www.lundix.se/spc-bridge-generic/) from Lundix IT.
- Home Assistant system, Core version >= 2024.9.0, Frontend version >= 20240809.0

> [!NOTE]
> The software module **SPC Web Gateway** isn't supported by this integration.

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

Before proceeding with the installation of this custom integration, make sure you have the the SPC Bridge Generic (lite) installed and properly configured.

### HACS

Add `Lundix-IT/spcbridge` as a custom repostiory in [HACS](https://www.hacs.xyz/) and add the component `Vanderbilt SPC Bridge`.

### Manual installation

You can also install the component manually as described below. You will need access to the Home Assistant filesystem, e.g., via the SSH add-on.

1. Download the [latest release](https://github.com/Lundix-IT/spcbridge/releases) of the **spcbridge.zip** file and extract it into the `config/custom_components` directory in your HA installation. (If the `custom_components` directory does not exist, create it.)
2. Restart HA to load the integration into HA.
3. Go to **Settings -> Devices & services** and click on the **Add integration** button. Look for SPC Bridge and click to add it.
4. Follow the configuration instructions.

## User and Pin codes
To be able to identify the SPC user by the entered Keypad code (or user code in automaion actions) you have to select between two methods:

#### Method 1 - Include the SPC User ID in the Keypad Code
Enter the SPC user's ID followed by their PIN code. For example:
- For a user with ID 3 and PIN code 1289, enter 31289.
- For a user with ID 21 and PIN code 987077, enter 21987077.
> [!NOTE]
> This method is recommended because SPC user credentials do not need to be stored in the Home Assistant system, but it only works for users who have not been assigned a web password in the SPC system. The user profile for the user also need to have **User Rights - System > Web Access** enabled.

#### Method 2 - Link Keypad Codes to SPC Users
Manually link the Keypad codes to the corresponding SPC credentials. If you choose this method, you have to define the linking table in the configuration of the integration.

## Devices
### SPC Bridge
**Device Name:** SPC Bridge<br>
Logical representation of the SPC Bridge. Has no entities.

### Alarm System (panel)
**Device Name:** SPC 4000/5000/6000<br>
Logical representation of the Alarm System (all areas).
#### Entities
| Entity             | Entity ID                                 | Values                  | Description                                    |
| ------------------ | ----------------------------------------- | ----------------------- | ---------------------------------------------- |
| `Arm mode`         | `sensor.<device_name>_arm_mode`           | `Disarmed`, `Partset A`, `Partset B`, `Armed`, `Partset A Partly`, `Partset B Partly`, `Armed Partly`, `Unknown`   | The current active arm mode.                |
| `Event message`    | `sensor.<device_name>_event_message`      | SPC events              | SPC events as text                             |
| `Fire`             | `binary_sensor.<device_name>_fire`        | `Off`, `On`             | System has an active fire alarm                |
| `Intrusion`        | `binary_sensor.<device_name>_intrusion`   | `Off`, `On`             | System has an active intrusion alarm           |
| `Problem`          | `binary_sensor.<device_name>_problem`     | `Off`, `On`             | System has an active problem alarm             |
| `Tamper`           | `binary_sensor.<device_name>_tamper`      | `Off`, `On`             | System has an active tamper alarm              |
| `Verified`         | `binary_sensor.<device_name>_verified`    | `Off`, `On`             | System has an active verified alarm            |

#### Automation Triggers
`Arm mode` is available as an **Entity** trigger. Click **Add trigger -> Entity -> State** and select the `<device name> Arm mode` entity and the from/to values.<br>
*Example:*  `When SPC4000 Arm mode changes from Disarmed to Armed`

`Fire`, `Intrusion`, `Problem`, `Tamper` and `Verified` can be used as both **Device** and **Entity** triggers.<br>
*Example:* `Garage Intrusion turned on`

#### Automation Conditions
`Arm mode` is available as an **Entity** condition. Click **Add condition -> Entity -> State** and select the `<device name> Arm mode` entity and the state.<br>
*Example:*  `Confirm SPC4000 Arm mode is Disarmed`

`Fire`, `Intrusion`, `Problem`, `Tamper` and `Verified` can be used as both **Device** and **Entity** conditions.<br>
*Example:* `SPC4000 Intrusion is on`

#### Automation Actions
Following commands are available for controlling a Alarm System (panel):
- Disarm (all areas)
- Partset A (all areas)
- Partset B (all areas)
- Arm (all areas)
- Arm and bypass open zones (all areas)
- Arm delayed (all areas)
- Arm delayed and bypass open zones (all areas)
- Clear all alerts

To define an action, click **Add action -> Other actions -> Vanderbilt SPC Bridge -> SPC Panel Command** and select an Alarm System and command. You need also enter a user code, see section **User and PIN codes** above.

### Alarm Areas
**Device Name:** Area name defined in SPC<br>
Logical representation of the alarm areas.
#### Entities
| Entity             | Entity ID                                 | Values                  | Description                                    |
| ------------------ | ----------------------------------------- | ----------------------- | ---------------------------------------------- |
| `Arm mode`         | `sensor.<device_name>_arm_mode`           | `Disarmed`, `Partset A`, `Partset B`, `Armed`, `Unknown`   | The current active arm mode.                |
| `Fire`             | `binary_sensor.<device_name>_fire`        | `Off`, `On`             | Alarm area has an active fire alarm                |
| `Intrusion`        | `binary_sensor.<device_name>_intrusion`   | `Off`, `On`             | Alarm area has an active intrusion alarm           |
| `Problem`          | `binary_sensor.<device_name>_problem`     | `Off`, `On`             | Alarm area has an active problem alarm             |
| `Tamper`           | `binary_sensor.<device_name>_tamper`      | `Off`, `On`             | Alarm area has an active tamper alarm              |
| `Verified`         | `binary_sensor.<device_name>_verified`    | `Off`, `On`             | Alarm area has an active verified alarm            |

#### Extra attributes
The entity `Arm mode` has following extra attributes that can be used for automation:
| Attribute               | Values                                 | Description                                                |
| ----------------------- | ---------------------------------------| ---------------------------------------------------------- |
| `Last disarmed user`    | SPC user name                          | The name of the SPC user who last disarmed the area        |
| `Last armed user`       | SPC user name                          | The name of the SPC user who last armed (fullset) the area    |

#### Automation Triggers
`Arm mode` is available as an **Entity** trigger. CLick **Add trigger -> Entity -> State** and select the `Arm mode` entity and the from/to values.<br>
*Example:*  `When Garage Arm mode changes from Disarmed to Armed`

`Fire`, `Intrusion`, `Problem`, `Tamper` and `Verified` can be used as both **Device** and **Entity** triggers.<br>
*Example:* `Garage Intrusion turned on`

#### Automation Conditions
`Arm mode` is available as an **Entity** condition. Click **Add condition -> Entity -> State** and select the `Arm mode` entity and the state.<br>
*Example:*  `Confirm Garage Arm mode is Disarmed`

`Fire`, `Intrusion`, `Problem`, `Tamper` and `Verified` can be used as both **Device** and **Entity** conditions.<br>
*Example:* `Garage Intrusion is on`

The attributes `Last disarmed/armed user` is available as **Entity** conditions. Click **Add condition -> Entity -> State** and select the `Arm mode` entity, the attribute `Last disarmed/armed user` and enter the name of the SPC user in the state field.<br>
*Example:* `Confirm Last armed user of Garage is John`

#### Automation Actions
Following commands are available for controlling alarm areas:
- Disarm
- Partset A
- Partset B
- Arm
- Arm and bypass open zones
- Arm delayed
- Arm delayed and bypass open zones

To define an action, click **Add action -> Other actions -> Vanderbilt SPC Bridge -> SPC Area Command** and select an Alarm Area and command. You need also enter a user code, see section **User and PIN codes** above.

### Alarm Zones
**Device Name:** Zone name defined in SPC<br>
Logical representation of the alarm zones. Following sensor types are supported:
- Motion sensor
- Door contact
- Window contact sensor
- Smoke sensor
- Other

You determine the zones's sensor type when you include the section in Home Assistant.

#### Entities
| Entity             | Entity ID                                 | Values                  | Description                                    |
| ------------------ | ----------------------------------------- | ----------------------- | ---------------------------------------------- |
| `Motion`           | `binary_sensor.<device_name>_motion`      | `Clear`, `Detected`     | Motion sensor has detected motion              |
| `Door`             | `binary_sensor.<device_name>_door`        | `Closed`, `Open`        | Door contact sensor is closed/open             |
| `Window`           | `binary_sensor.<device_name>_window`      | `Closed`, `Open`        | Window contact sensor is closed/open           |
| `Smoke`            | `binary_sensor.<device_name>_smoke`       | `Clear`, `Detected`     | Smoke sensor has detected smoke                |
| `Other`            | `binary_sensor.<device_name>`             | `Off`, `On`             | "Other" sensor is off (closed) / on (open)     |
| `Alarm`            | `binary_sensor.<device_name>_alarm`       | `Off`, `On`             | Zone is alarming                               |
| `Problem`          | `binary_sensor.<device_name>_problem`     | `Off`, `On`             | Zone has a problem                             |
| `Tamper`           | `binary_sensor.<device_name>_tamper`      | `Off`, `On`             | Zone has detected a tamper                     |
| `Inhibited`        | `binary_sensor.<device_name>_inhibited`   | `Off`, `On`             | Zone is inhibited                              |
| `Isolated`         | `binary_sensor.<device_name>_isolated`    | `Off`, `On`             | Zone is isolated                               |

#### Automation Triggers
All zone entities can be used as both **Device** and **Entity** triggers.<br>
*Example:* `PIR Living Room started detecting motion`

#### Automation Conditions
All zone entities can be used as both **Device** and **Entity** conditions.<br>
*Example:* `Bed Room Window is open`

#### Automation Actions
Following commands are available for controlling alarm zones:
- Inhibit
- De-inhibit
- Isolate
- De-isolate

To define an action, click **Add action -> Other actions -> Vanderbilt SPC Bridge -> SPC Zone Command** and select an Alarm Zone and command. You need also enter a user code, see section **User and PIN codes** above.

### Outputs (mapping gates and virtual zones)
**Device Name:** Name of mapping gate defined in SPC<br>
Logical representation of the SPC system's mapping gates and virtual zone.
#### Entities
| Entity             | Entity ID                                 | Values                  | Description                                    |
| ------------------ | ----------------------------------------- | ----------------------- | ---------------------------------------------- |
| `State`            | `binary_sensor.<device_name>_state`       | `Off`, `On`             | Mapping gate state is off or on                |

#### Automation Triggers
The `State` entity can be used as both a **Device** and an **Entity** trigger.<br>
*Example:* `Outdoor lighting State turned on`

#### Automation Conditions
The ´State` entity can be used as both a **Device** and an **Entity** condition.<br>
*Example:* `Outdoor lighting State is on`

#### Automation Actions
Following commands are available for controlling outputs:
- On
- Off

To define an action, click **Add action -> Other actions -> Vanderbilt SPC Bridge -> SPC Output Command** and select an Output and command. You need also enter a user code, see section **User and PIN codes** above.

### Door Locks
**Device Name:** Name of door defined in SPC<br>
Logical representation of the SPC system's door locks.
#### Entities
| Entity                      | Entity ID                                       | Values                  | Description                                    |
| --------------------------- | ----------------------------------------------- | ----------------------- | ---------------------------------------------- |
| `Door Mode`                 | `sensor.<device_name>_door_mode`                | `Unlocked`, `Normal`, `Locked`, `Unknown`           | Door mode          |
| `Last entry denied user`    | `sensor.<device_name>_last_entry_denied_user`   | SPC user name           | Name of user who was last denied entry         |
| `Last entry granted user`   | `sensor.<device_name>_last_entry_granted_user`  | SPC user name           | Name of user who was last granted entry        |
| `Last exit denied user`     | `sensor.<device_name>_last_exit_denied_user`    | SPC user name           | Name of user who was last denied exit          |
| `Last exit granted user`    | `sensor.<device_name>_last_exit_granted_user`   | SPC user name           | Name of user who was last granted exit         |

#### Automation Triggers
`Door Mode` is available as an **Entity** trigger. Click **Add trigger -> Entity -> State** and select the `<device name> Door Mode` entity and the from/to values.<br>
*Example:*  `When Entrance Door Mode changes from Locked to Unlocked`

#### Automation Conditions
All door locks entities are available as **Entity** conditions. Click **Add condition -> Entity -> State** and select entity and state.<br>
*Example:* `Confirm Entrance Last entry granted user is John`

#### Automation Actions
Following commands are available for controlling door locks:
- Open momentarily (Only possible in Normal door mode)
- Set door mode to Unlocked
- Set door mode to Normal
- Set door mode to Locked

To define an action, click **Add action -> Other actions -> Vanderbilt SPC Bridge -> SPC Door Command** and select a Door and command. You need also enter a user code, see section **User and PIN codes** above.
