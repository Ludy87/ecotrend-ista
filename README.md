# ista EcoTrend Version 2

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://img.shields.io/badge/My-HACS:%20REPOSITORY-000000.svg?&style=for-the-badge&logo=home-assistant&logoColor=white&color=049cdb)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Ludy87&repository=ecotrend-ista&category=integration)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge&logo=home-assistant&logoColor=white)](https://github.com/hacs/integration)
![Validate with hassfest and HACS](https://img.shields.io/github/actions/workflow/status/Ludy87/ecotrend-ista/hassfest.yaml?label=Validate%20with%20hassfest%20and%20hacs&style=for-the-badge&logo=home-assistant&logoColor=white)\
[![GitHub license](https://img.shields.io/github/license/Ludy87/ecotrend-ista?label=📜%20License&style=for-the-badge&logo=informational&logoColor=white)](LICENSE)
[![GitHub release (latest by date)](https://img.shields.io/github/v/release/Ludy87/ecotrend-ista?style=for-the-badge&logo=GitHub&logoColor=white)](https://github.com/Ludy87/ecotrend-ista/releases)
![GitHub Release Date](https://img.shields.io/github/release-date/Ludy87/ecotrend-ista?style=for-the-badge&logo=GitHub&logoColor=white)
[![GitHub stars](https://img.shields.io/github/stars/Ludy87/ecotrend-ista?style=for-the-badge&logo=GitHub&logoColor=white)](https://github.com/Ludy87/ecotrend-ista/stargazers)
[![GitHub issues](https://img.shields.io/github/issues/Ludy87/ecotrend-ista?style=for-the-badge&logo=GitHub&logoColor=white)](https://github.com/Ludy87/ecotrend-ista/issues)
![Github All Releases](https://img.shields.io/github/downloads/Ludy87/ecotrend-ista/total.svg?style=for-the-badge&logo=GitHub&logoColor=white)\
![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg?style=for-the-badge&logoColor=white)\
[![✨ Wishlist from Amazon ✨](https://img.shields.io/static/v1.svg?label=✨%20Wishlist%20from%20Amazon%20✨&message=📖&color=green&logo=amazon&style=for-the-badge&logoColor=white)](https://smile.amazon.de/registry/wishlist/2MX8QK8VE9MV1)
[![Buy me a coffee](https://img.shields.io/static/v1.svg?label=Buy%20me%20a%20coffee&message=donate&style=for-the-badge&color=black&logo=buy%20me%20a%20coffee&logoColor=white&labelColor=orange)](https://www.buymeacoffee.com/ludy87)

---
![ista EcoTrend V2](https://github.com/Ludy87/ecotrend-ista/blob/main/image/logo_new@2x.png?raw=true)

## Installation

### MANUAL INSTALLATION

Copy the ecotrend_ista [last Releae](https://github.com/Ludy87/ecotrend-ista/releases) folder and all of its contents into your Home Assistant's custom_components folder. This folder is usually inside your /config folder. If you are running Hass.io, use SAMBA to copy the folder over. If you are running Home Assistant Supervised, the custom_components folder might be located at /usr/share/hassio/homeassistant. You may need to create the custom_components folder and then copy the localtuya folder and all of its contents into it Alternatively, you can install localtuya through HACS by adding this repository.

### INSTALLATION mit HACS

1. Ensure that [HACS](https://hacs.xyz/) is installed.
2. Search for and install the "__ecotrend ista Integration__" integration. [![GitHub release (latest by date)](https://img.shields.io/github/v/release/Ludy87/ecotrend-ista?style=for-the-badge&logo=GitHub)](https://github.com/Ludy87/ecotrend-ista/releases)
3. [Configuration for the `ista EcoTrend` integration is now performed via a config flow as opposed to yaml configuration file.](https://github.com/Ludy87/ecotrend-ista#basis-configuration)
4. Restart Home Assistant.

---

## Basis Configuration

1. Go to HACS -> Integrations -> Click "+"
2. Search for "ista EcoTrend" repository and add to HACS
3. Restart Home Assistant when it says to.
4. In Home Assistant, go to Configuration -> Integrations -> Click "+ Add Integration"
5. Search for "ista EcoTrend" and follow the instructions to setup.

ista EcoTrend should now appear as a card under the HA Integrations page with "Configure" selection available at the bottom of the card.

---

## Two-factor authentication (experimental)

- [Two-factor authentication deutsch](TWO_FACTOR_AUTHENTICATION_DE.md)
- [Two-factor authentication english](TWO_FACTOR_AUTHENTICATION_EN.md)

---

## Debug

```yaml
logger:
  logs:
    custom_components.ecotrend_ista: debug
```
