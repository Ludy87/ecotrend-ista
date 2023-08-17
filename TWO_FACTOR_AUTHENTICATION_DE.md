# Two-factor authentication

## Steps

### aktivier debugging <https://github.com/Ludy87/ecotrend-ista#debug>

### Gehe zu <https://ecotrend.ista.de/> und logge dich ein. Danach auf Menü, wähle "Benutzerkonto" und scrolle zu "Zwei-Stufen-Authentifizierung" und klicke auf "Hinzufügen"

![Two-factor authentication 1](./image/two_factor_authentication_1.png)

### Klicke auf "Hat der Scan nicht funktioniert?" unter dem QR-Code

![Two-factor authentication 2](./image/two_factor_authentication_2.png)

### Bei Punkt 2 wird der Schlüssel angezeigt der kopiert werden muss (am besten aufschreiben wird zweimal benötigt)

![Two-factor authentication 3](./image/two_factor_authentication_3.png)

### erstell nun einen OTP Sensor in Home-Assistant und startet Home-Assistant neu

<https://www.home-assistant.io/integrations/otp#configuration>

```yaml
# Example configuration.yaml entry
sensor:
  - platform: otp
    token: KEY_FROM_ECOTREND
```

### Schreibe einen Namen in "Gerätename" bevor du den Code von OTP Sensor kopierst, danach kopierst du den generierten Code und fügst ihn ein (Achtung, der Code ist nur 30sec gültig)

![Two-factor authentication 4](./image/two_factor_authentication_4.png)

### Jetzt kann die Integration [![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://img.shields.io/badge/My-HACS:%20REPOSITORY-000000.svg?&style=for-the-badge&logo=home-assistant&logoColor=white&color=049cdb)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Ludy87&repository=ecotrend-ista&category=integration) angelegt werden

### gebe die Daten ein

![Two-factor authentication 5](./image/two_factor_authentication_5.png)

### Sollte etwas nicht funktionieren, lassen sie 30 minuten vergehen, bis sie es wiederholen - Ista hat eine Bruceforce detektion
