# Two-factor authentication

## Steps

### enable debugging <https://github.com/Ludy87/ecotrend-ista#debug>

### Go to <https://ecotrend.ista.de/>  and log in. After that, click on the menu, select "Benutzerkonto" and scroll down to "Zwei-Stufen-Authentifizierung" then click on "Hinzufügen"

![Two-factor authentication 1](./image/two_factor_authentication_1.png)

### Click on "Hat der Scan nicht funktioniert?" below the QR code

![Two-factor authentication 2](./image/two_factor_authentication_2.png)

### In step 2, the key will be displayed, which needs to be copied (it's best to write it down, as it will be required twice)

![Two-factor authentication 3](./image/two_factor_authentication_3.png)

### Now create an OTP sensor in Home-Assistant and restart Home-Assistant

<https://www.home-assistant.io/integrations/otp#configuration>

```yaml
# Example configuration.yaml entry
sensor:
  - platform: otp
    token: KEY_FROM_ECOTREND
```

### Write a name in the "Gerätename" before copying the code from the OTP sensor; then, paste the generated code (Note: the code is only valid for 30 seconds)

![Two-factor authentication 4](./image/two_factor_authentication_4.png)

### Now the integration can be set up [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://img.shields.io/badge/My-HACS:%20REPOSITORY-000000.svg?&style=for-the-badge&logo=home-assistant&logoColor=white&color=049cdb)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Ludy87&repository=ecotrend-ista&category=integration)

### Enter the data

![Two-factor authentication 5](./image/two_factor_authentication_5.png)

### If something doesn't work, wait for 30 minutes before trying again - Ista has a brute force detection
