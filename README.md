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

## Notes

- This integration uses `pyqvrpro-client` for API communication.
- Metadata events are queried from `/{prefix}/qvrip/Metadata/Query`.
