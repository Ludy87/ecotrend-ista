# Podpora českého portálu ista EcoTrend

Integrace podporuje české účty dostupné přes portál `https://ecotrend.ista.cz/`. Data získává přímo z backendu používaného zákaznickou aplikací ista EcoTrend; nepoužívá scraping webové stránky ani automatizovaný prohlížeč.

Jde o neoficiální komunitní implementaci, která není spojena se společností ista ani jí podporována. Backend se může bez předchozího upozornění změnit nebo omezit přístup. Integraci používejte pouze s účtem a údaji, ke kterým máte oprávněný přístup.

## Nastavení

1. Nainstalujte integraci přes HACS a restartujte Home Assistant.
2. V Home Assistantu otevřete **Nastavení → Zařízení a služby → Přidat integraci**.
3. Vyhledejte **ista EcoTrend**.
4. Jako přihlašovací URL vyberte `https://ecotrend.ista.cz/`.
5. Zadejte uživatelské jméno a heslo českého účtu ista.
6. Doporučený interval aktualizace je 24 hodin.

Český backend aktuálně nevyužívá kód dvoufázového ověření. Kratší interval, například jedna hodina, je vhodný pouze pro dočasné ověření synchronizace.

## Dostupná data

Integrace vytváří:

- samostatný senzor posledního dostupného kumulativního stavu každého fyzického měřidla,
- poslední dostupnou denní spotřebu vytápění, teplé vody a studené vody,
- spotřebu za poslední dostupný měsíc,
- senzor **Data dostupná do**, který ukazuje poslední datum zveřejněné společností ista,
- dlouhodobé statistiky denní spotřeby pro vytápění, teplou vodu a studenou vodu.

Počet fyzických měřidel závisí na konkrétním bytě a účtu. Historická data poskytuje API souhrnně podle typu spotřeby, nikoli samostatně pro každý radiátor nebo vodoměr.

## Historie a zpoždění

ista může hodnoty zveřejňovat s několikadenním zpožděním. Integrace zachovává skutečné datum měření a opožděnou hodnotu nevydává za dnešní spotřebu.

Při aktualizaci se načítá denní historie za posledních 12 měsíců. Hodnoty se ukládají do dlouhodobých statistik Home Assistantu a lze je seskupovat po dnech nebo měsících. Měsíční senzor samotný ukazuje pouze poslední dostupný měsíc; starší měsíce jsou dostupné prostřednictvím dlouhodobých statistik, nikoli jako zpětně vytvořené stavy entity.

Pokud ista později opraví starší denní hodnotu, integrace aktualizuje daný den a přepočítá navazující kumulativní statistické body.

## Jednotky

- Teplá a studená voda se vykazuje v m³.
- Indikátory topných nákladů se vykazují v alokačních jednotkách, nikoli v kWh.
- Fyzická měřidla zobrazují kumulativní stav. Denní a měsíční senzory zobrazují spotřebu za dané období.

## Známá omezení

- Externí dlouhodobé statistiky vyžadují aktivní komponentu Recorder.
- Integrace aktualizuje data v nastaveném intervalu, nikoli v konkrétní denní hodinu.
- Nově přidané nebo vyměněné měřidlo se vystaví po opětovném načtení integrace.
- Při změně přihlašovacích údajů je zatím potřeba účet v integraci znovu nakonfigurovat; samostatný reautentizační postup není implementován.
- Dostupný rozsah historie určuje backend ista. Integrace aktuálně požaduje posledních 12 měsíců.
