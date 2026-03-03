# QNAP QVR Connector (HACS)

Custom Home Assistant integration for QNAP QVR Pro/Elite/Surveillance.

## Features

- Camera entities from QVR channels
- Metadata Vault events exposed to Advanced Camera Card timeline
- Text sensors per metadata event type (latest event message + count)
- Recording proxy endpoint for card playback

## Install in HACS (manual custom repository)

1. HACS -> Integrations -> menu (3 dots) -> Custom repositories
2. Add repository URL of this repo
3. Category: **Integration**
4. Install **QNAP QVR Connector**
5. Restart Home Assistant

## Configuration

1. Go to **Settings -> Devices & Services -> Add Integration**.
2. Search for **QNAP QVR Connector**.
3. Fill in host, ports, username, and password.
4. Finish the flow and note the generated config entry ID.

## Advanced Camera Card example

```yaml
type: custom:advanced-camera-card
cameras:
  - camera_entity: camera.qvr_camera_1
    engine: qvr
    qvr:
      entry_id: "<HA_CONFIG_ENTRY_ID>"
      camera_guid: "<QVR_CHANNEL_GUID>"
```

## Manual install (without HACS)

1. Copy `custom_components/qnap_qvr_connector` to your HA config folder under `custom_components/`.
2. The integration auto-installs `pyqvrpro-client` from GitHub release tag `v0.2.0.1002`.
3. Restart Home Assistant.

## Notes

- This integration uses `pyqvrpro-client` for API communication.
- Metadata events are queried from `/{prefix}/qvrip/Metadata/Query`.
