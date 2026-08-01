const assert = require("node:assert/strict");
const fs = require("node:fs");
const test = require("node:test");
const vm = require("node:vm");

function loadCard() {
  const registered = new Map();
  const context = {
    console,
    CustomEvent: class {},
    Event: class {},
    HTMLElement: class {
      attachShadow() {
        this.shadowRoot = {};
      }
    },
    customElements: {
      define(name, klass) {
        registered.set(name, klass);
      },
    },
    document: {},
    history: {},
    window: { customCards: [] },
  };
  vm.createContext(context);
  vm.runInContext(
    fs.readFileSync("custom_components/life_events/life-events-card.js", "utf8"),
    context
  );
  return registered.get("life-events-card");
}

function state(name, days, eventId) {
  return {
    state: String(days),
    attributes: {
      name,
      event_id: eventId,
      event_type: "birthday",
      next_date: "2026-08-10",
    },
  };
}

test("normal mode sorts by date and applies max_events", () => {
  const Card = loadCard();
  const card = new Card();
  card.setConfig({ max_events: 1 });
  card._hass = {
    states: {
      "sensor.life_events_zara": state("Zara", 20, "zara"),
      "sensor.life_events_amy": state("Amy", 2, "amy"),
    },
  };

  assert.deepEqual(Array.from(card._getEvents(), (event) => event.name), ["Amy"]);
});

test("management mode shows every event alphabetically", () => {
  const Card = loadCard();
  const card = new Card();
  card.setConfig({ management_mode: true, max_events: 1 });
  card._hass = {
    states: {
      "sensor.life_events_zara": state("Zara", 2, "zara"),
      "sensor.life_events_amy": state("Amy", 20, "amy"),
    },
  };

  assert.deepEqual(Array.from(card._getEvents(), (event) => event.name), ["Amy", "Zara"]);
});

test("optimistically deleted events stay hidden", () => {
  const Card = loadCard();
  const card = new Card();
  card.setConfig({ management_mode: true });
  card._hass = {
    states: {
      "sensor.life_events_amy": state("Amy", 2, "amy"),
    },
  };
  card._deletedEventIds.add("amy");

  assert.equal(card._getEvents().length, 0);
});
