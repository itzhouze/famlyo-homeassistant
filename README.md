# Famlyo für Home Assistant

Einkaufsliste und Bestand deines [Famlyo](https://famlyo.de)-Haushalts in Home Assistant:

- **Einkaufsliste als Todo-Liste** — ansehen, ergänzen, abhaken, entfernen. Funktioniert direkt mit Assist: *„Füge zwei Liter Milch zur Einkaufsliste hinzu"* — auch über lokale Sprachassistenten wie umgebaute Echos.
- **Sensoren** — offene Artikel, nicht vorrätig/knapp, läuft bald ab (die Produkte stehen als Attribute dabei).
- **Aktion `famlyo.get_stock`** — „Haben wir Milch?" für Skripte, Automationen und Sprach-Assistenten.

Die Integration spricht ausschließlich die öffentliche [Famlyo API](https://api.famlyo.de/v1/openapi.json). Was sie tut, sieht deine Familie in Famlyo so, als hättest du es getan.

## Voraussetzungen

- Famlyo-Konto, Haushalt mit **Famlyo Premium**
- Home Assistant 2025.4 oder neuer

## Installation (HACS)

1. HACS → ⋮ → **Benutzerdefinierte Repositories** → `https://github.com/itzhouze/famlyo-homeassistant`, Typ *Integration*.
2. „Famlyo" installieren, Home Assistant neu starten.
3. In der Famlyo-App: **Einstellungen → Meine Integrationen → API-Zugriff → API-Token erstellen**. Rechte nach Bedarf wählen, Token kopieren.
4. Home Assistant: **Einstellungen → Geräte & Dienste → Integration hinzufügen → Famlyo**, Token einfügen.

Der API-Token gilt für genau einen Haushalt. Für mehrere Haushalte legst du je einen Token an und richtest die Integration mehrfach ein.

## Was geht — und was bewusst nicht

| In Home Assistant | In Famlyo |
|---|---|
| Artikel hinzufügen („2 Liter Milch, Brot") | wird verstanden wie ein Diktat: Produkt, Menge, Sorte |
| Abhaken / zurücknehmen | genau wie in der App, inklusive Benachrichtigung an die Familie |
| Offenen Artikel löschen | entfernt |
| **Abgehakten** Artikel löschen („Erledigte entfernen") | **abgelehnt** — er wartet aufs Einräumen in den Bestand. Bitte in der App einräumen. |
| Artikel umbenennen | nicht möglich — Produkte haben in Famlyo feste Namen |

Die Liste zeigt offene Artikel und alles, was heute abgehakt wurde.

## Sprachbefehle

Für Assist reicht die Todo-Liste: Gib der Entität in Home Assistant den Alias **„Einkaufsliste"**, dann funktioniert *„Setze Brot auf die Einkaufsliste"*.

„Haben wir noch Milch?" als eigener Satz (`config/custom_sentences/de/famlyo.yaml`):

```yaml
language: de
intents:
  FamlyoStock:
    data:
      - sentences:
          - "(haben|hab) wir [noch] {produkt}"
          - "ist [noch] {produkt} da"
lists:
  produkt:
    wildcard: true
```

und in `configuration.yaml`:

```yaml
intent_script:
  FamlyoStock:
    action:
      - action: famlyo.get_stock
        data:
          query: "{{ produkt }}"
        response_variable: stock
    speech:
      text: >
        {% if stock.in_stock %}Ja, {{ stock.item.amount_text }} {{ stock.item.name }}.
        {% elif stock.matched_name %}Nein, {{ stock.matched_name }} ist alle.
        {% else %}Das kenne ich in eurem Bestand nicht.{% endif %}
```

## Direkt per REST (ohne Integration)

```yaml
rest_command:
  famlyo_add:
    url: https://api.famlyo.de/v1/shopping/items
    method: POST
    headers:
      Authorization: !secret famlyo_token   # "Bearer famlyo_pat_…"
    content_type: application/json
    payload: '{"text": "{{ text }}"}'
```

Vollständige Beschreibung aller Endpunkte: <https://api.famlyo.de/v1/openapi.json>

## Datenschutz

Der API-Token liegt nur in deiner Home-Assistant-Konfiguration. Famlyo speichert ihn nicht, nur einen Fingerabdruck. Entfernst du ihn in der App, verliert Home Assistant sofort den Zugriff; verlässt du den Haushalt, ebenso.
