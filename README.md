# 🎂 Life Events for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub release](https://img.shields.io/github/release/calebgab/ha-life-events.svg)](https://github.com/calebgab/ha-life-events/releases)
[![License](https://img.shields.io/github/license/calebgab/ha-life-events)](LICENSE)

**The all-in-one birthday and anniversary integration for Home Assistant.**

Track birthdays, wedding anniversaries, and custom recurring dates — with countdown sensors, a calendar entity, a beautiful Lovelace card, and built-in notification support. No YAML required.

---

## ✨ Features

- **Sensor per event** — `sensor.life_events_<n>` with state = days until next occurrence
- **Rich attributes** — next date, age/years turning, event type, original date
- **Calendar entity** — `calendar.life_events` integrates with the HA Calendar dashboard
- **Lovelace card** — polished card with urgency colouring, type badges, age display
- **Notification blueprint** — one-click automation for day-of and advance notifications
- **UI-only config** — add/edit/remove events from the HA UI, no YAML editing
- **Event types** — Birthday, Anniversary, Custom (with your own label)
- **Year-optional** — track day/month only when the birth year isn't known
- **HA events** — `life_events_today` and `life_events_upcoming` fired for automation use

![Life Events Lovelace Card](images/lovelacecard.png)

---

## 📦 Installation

### Via HACS (recommended)

1. Open HACS → Integrations → ⋮ → Custom repositories
2. Add `https://github.com/calebgab/ha-life-events` as type **Integration**
3. Search "Life Events" and install
4. Restart Home Assistant
5. Go to **Settings → Devices & Services → Add Integration → Life Events**

### Manual

1. Copy `custom_components/life_events/` into your HA `custom_components/` folder
2. Restart Home Assistant
3. Go to **Settings → Devices & Services → Add Integration → Life Events**

---

## ⚙️ Configuration

After adding the integration, go to **Settings → Devices & Services → Life Events → Configure** to add your events.

### Adding an event

Select **➕ Add new event** in the dropdown and click Submit. Enter details as required and click Submit.

![Add New Event](images/addNewEvent.png)
![Test Event and Main Buttons](images/testEventAndMainButtons.png)

| Field | Description |
|---|---|
| Name | Person or event name (e.g. `Sarah`, `Mom & Dad`) |
| Date | `YYYY-MM-DD` (e.g. `1990-03-15`) or `MM-DD` if year unknown |
| Type | `birthday`, `anniversary`, or `custom` |
| Custom label | Label used if type is `custom` (e.g. `Gotcha Day`) |
| Icon | MDI icon override (e.g. `mdi:dog`) |
| Year unknown | Check if you only know the day/month — hides age/years |

Once you've added all the events you want, in the Configure window, scroll down to **✅ Save and Finish** and click Submit.

![Save and Finish](images/saveAndFinish.png)

---

### Deleting an event

Go to **Settings → Devices & Services → Life Events → Configure** and select your event from the dropdown and click Submit.

![Select Event](images/testEvent.png)

Then tick **Delete this event** and click Submit.

![Delete Event](images/deleteEvent.png)

Then from the dropdown, select **✅ Save and finish** and click Submit.

![Save and Finish](images/saveAndFinish.png)

---

## 🃏 Lovelace Card

The card resource is registered automatically when the integration loads — no manual resource configuration needed.

### Add the card

**Recommended:** Edit your dashboard, click **Add Card**, and search for **Life Events Card** in the card picker. This gives you a visual editor to configure the card without any YAML.

**Via YAML:** Alternatively, add a Manual card with the following configuration:

```yaml
type: custom:life-events-card
title: Upcoming Celebrations
max_events: 10
show_types:
  - birthday
  - anniversary
  - custom
```

### Card options

| Option | Type | Default | Description |
|---|---|---|---|
| `title` | string | `Life Events` | Card heading |
| `max_events` | number | `10` | Maximum number of events to display |
| `show_types` | list | all types | Filter to only these event types |
| `show_past_days` | number | `0` | Also show events up to N days after they passed |

---

## 🔔 Notification Blueprint

Import the bundled blueprint to get notified on the day of an event (and/or days before):

[![Import Blueprint](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https://raw.githubusercontent.com/calebgab/ha-life-events/main/blueprints/automation/life_events_notify.yaml)

Or manually copy `blueprints/automation/life_events_notify.yaml` to your HA blueprints folder.

The blueprint runs daily at a time you choose, checks all your Life Events sensors, and sends a notification for any events that are today or a set number of days away.

---

## 📡 Sensor Attributes

Each `sensor.life_events_<n>` exposes:

| Attribute | Example | Description |
|---|---|---|
| `state` | `5` | Days until next occurrence |
| `next_date` | `2025-06-12` | Date of next occurrence |
| `days_until` | `5` | Same as state, for template use |
| `years_at_next` | `35` | Age or years at next occurrence (`null` if year unknown) |
| `event_type` | `birthday` | `birthday`, `anniversary`, or `custom` |
| `event_label` | `Birthday` | Human-readable label |
| `year_unknown` | `false` | Whether the birth/start year is known |
| `original_date` | `1990-06-12` | The date as entered |

---

## 🤖 Automation Examples

### Custom notification using sensor attributes

```yaml
alias: "Birthday notification"
trigger:
  - platform: template
    value_template: "{{ states('sensor.life_events_sarah') | int == 0 }}"
action:
  - service: notify.mobile_app_my_phone
    data:
      title: "🎂 Happy Birthday!"
      message: >
        Today is {{ state_attr('sensor.life_events_sarah', 'event_label') }}
        for Sarah — turning {{ state_attr('sensor.life_events_sarah', 'years_at_next') }}!
```

### Using the HA event directly

```yaml
trigger:
  - platform: event
    event_type: life_events_today
action:
  - service: notify.notify
    data:
      message: "{{ trigger.event.data.name }}'s {{ trigger.event.data.event_label }} is today!"
```

---

## 🙋 FAQ

**Can I have multiple events for the same person?**
Yes — just give them different names (e.g. `Sarah Birthday`, `Sarah Work Anniversary`).

**Will it handle leap-year birthdays (Feb 29)?**
Feb 29 birthdays are celebrated on Feb 28 in non-leap years.

**How do I show events on the Home Assistant calendar?**
The `calendar.life_events` entity is created automatically. Add it to your Calendar dashboard view.

---

## 🤝 Contributing

Issues and PRs welcome at [GitHub](https://github.com/calebgab/ha-life-events/issues).

## 📄 License

MIT License — see [LICENSE](LICENSE).
