# Cover Tilt

`cover_tilt` ist eine Home-Assistant-Integration, die zu einem bestehenden Cover
eine zusätzliche Lamellen-/Tilt-Steuerung bereitstellt.

## Installation via HACS

1. HACS öffnen.
2. **Integrationen** auswählen.
3. Über das Menü **Benutzerdefinierte Repositories** dieses Repository hinzufügen:
   `https://github.com/Jargendas/homeassistant-cover-tilt`
4. Als Kategorie **Integration** wählen.
5. **Cover Tilt** installieren und Home Assistant neu starten.

## Einrichtung

1. In Home Assistant zu **Einstellungen → Geräte & Dienste → Integration hinzufügen**.
2. **Cover Tilt** auswählen.
3. Folgende Werte setzen:
   - **Name** (optional)
   - **Cover-Entity** (bestehendes Cover)
   - **Zeit für volle Lamellenrotation (Sekunden)**

Danach steht eine neue Cover-Entity mit Tilt-Funktionen zur Verfügung.
