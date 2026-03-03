# QNAP QVR Connector — Testing Guide

## Prerequisites

- Home Assistant (Supervised, Core, or Container)
- QNAP NAS with QVR Pro or QVR Elite
- Network access to QVR from Home Assistant

## 1. Install pyqvrpro-client

```bash
pip install -e /path/to/pyqvrpro-client
```

For Home Assistant: The integration declares `requirements: ["pyqvrpro-client>=0.1.0"]` in manifest.json. HA will install it automatically when adding the integration if the package is published on PyPI. For local development:

- Copy `pyqvrpro-client` into your HA environment, or
- Publish to PyPI: `pip install build && python -m build pyqvrpro-client && twine upload dist/*`

## 2. Install the Integration

Copy the integration to Home Assistant:

```bash
cp -r qnap-qvr-connector/custom_components/qnap_qvr_connector /path/to/homeassistant/config/custom_components/
```

Restart Home Assistant.

## 3. Add the Integration

1. **Settings → Devices & Services → Add Integration**
2. Search for **QNAP QVR Connector**
3. Enter host (e.g. `192.168.1.100`), port (e.g. `8080`), username, password
4. Complete the config flow
5. Note the **Config Entry ID** (from the integration URL: `/config/integrations/integration/<entry_id>`)

## 4. Install Advanced Camera Card

1. Build the card:
   ```bash
   cd advanced-camera-card && yarn install && yarn run build
   ```

2. Copy `dist/advanced-camera-card.js` (and `.map` if needed) to HA `www/` or install via HACS.

3. Add the resource in Lovelace:
   ```yaml
   resources:
     - url: /local/advanced-camera-card.js
       type: module
   ```

## 5. Configure the Card

Example Lovelace config using QVR engine:

```yaml
type: custom:advanced-camera-card
cameras:
  - camera_entity: camera.qvr_channel_1
    engine: qvr
    qvr:
      entry_id: "<YOUR_CONFIG_ENTRY_ID>"
      camera_guid: "<optional_guid_if_filtering>"
```

Replace `<YOUR_CONFIG_ENTRY_ID>` with the integration’s config entry ID from step 3.

## 6. Verify

- **Cameras**: Camera entities should appear under the integration.
- **Snapshots**: Card should show live/snapshot for QVR cameras.
- **Timeline**: Surveillance Events (log_type=3) should appear on the timeline when using `engine: qvr`.

## Local Scripts (No HA)

From `d:\Code`:

```bash
# Load .env with QVR_HOST, QVR_PORT, QVR_USER, QVR_PASSWORD
python scripts/test_qvr_auth.py
python scripts/test_qvr_qvrentry.py
python scripts/test_qvr_cameras.py
python scripts/test_qvr_events.py
python scripts/test_qvr_metadata.py
```
