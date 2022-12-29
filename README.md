# ecotrend-ista

[ecotrend-ista](https://ecotrend.ista.de/) Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge&logo=appveyor)](https://github.com/hacs/integration)
[![GitHub release (latest by date)](https://img.shields.io/github/v/release/Ludy87/ecotrend-ista?style=for-the-badge&logo=appveyor)](https://github.com/Ludy87/ecotrend-ista/releases)
![GitHub Release Date](https://img.shields.io/github/release-date/Ludy87/ecotrend-ista?style=for-the-badge&logo=appveyor)
[![GitHub](https://img.shields.io/github/license/Ludy87/ecotrend-ista?style=for-the-badge&logo=appveyor)](LICENSE)
[![GitHub issues](https://img.shields.io/github/issues/Ludy87/ecotrend-ista?style=for-the-badge&logo=appveyor)](https://github.com/Ludy87/ecotrend-ista/issues)
[![Validate with hassfest and HACS](https://github.com/Ludy87/ecotrend-ista/actions/workflows/hassfest.yaml/badge.svg)](https://github.com/Ludy87/ecotrend-ista/actions/workflows/hassfest.yaml)

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://www.buymeacoffee.com/ludy87)

[✨ Wishlist from Amazon ✨](https://smile.amazon.de/registry/wishlist/2MX8QK8VE9MV1)

---
![ecotrend-ista-V2](https://github.com/Ludy87/ecotrend-ista/blob/main/image/logo@2x.png?raw=true)

## Installation

### MANUAL INSTALLATION

Copy the ecotrend_ista [last Releae](https://github.com/Ludy87/ecotrend-ista/releases) folder and all of its contents into your Home Assistant's custom_components folder. This folder is usually inside your /config folder. If you are running Hass.io, use SAMBA to copy the folder over. If you are running Home Assistant Supervised, the custom_components folder might be located at /usr/share/hassio/homeassistant. You may need to create the custom_components folder and then copy the localtuya folder and all of its contents into it Alternatively, you can install localtuya through HACS by adding this repository.

### INSTALLATION mit HACS

1. Ensure that [HACS](https://hacs.xyz/) is installed.
2. Search for and install the "__ecotrend ista Integration__" integration. [![GitHub release (latest by date)](https://img.shields.io/github/v/release/Ludy87/ecotrend-ista?style=for-the-badge&logo=appveyor)](https://github.com/Ludy87/ecotrend-ista/releases)
3. [Configuration for the `ecotrend_ista` integration is now performed via a config flow as opposed to yaml configuration file.](https://github.com/Ludy87/ecotrend-ista#basis-configuration)
4. Restart Home Assistant.

---

## Basis Configuration

1. Go to HACS -> Integrations -> Click "+"
2. Search for "ecotrend ista" repository and add to HACS
3. Restart Home Assistant when it says to.
4. In Home Assistant, go to Configuration -> Integrations -> Click "+ Add Integration"
5. Search for "ecotrend ista" and follow the instructions to setup.

ecotrend ista should now appear as a card under the HA Integrations page with "Configure" selection available at the bottom of the card.

---

## Debug

```yaml
logger:
  logs:
    custom_components.ecotrend_ista: debug
```

---
