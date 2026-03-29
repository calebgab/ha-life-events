/**
 * Life Events Card
 * A custom Lovelace card for the Life Events integration.
 * Displays upcoming birthdays, anniversaries, and custom events.
 *
 * Usage:
 *   type: custom:life-events-card
 *   title: Upcoming Celebrations   (optional)
 *   max_events: 10                 (optional, default 10)
 *   show_types: [birthday, anniversary, custom]  (optional, default all)
 *   show_past_days: 0              (optional, show events N days after they passed)
 */

const EVENT_ICONS = {
  birthday: "🎂",
  anniversary: "💍",
  custom: "⭐",
};

const EVENT_COLORS = {
  birthday: "#e8906a",
  anniversary: "#b07bbf",
  custom: "#6aace8",
};

const URGENCY_COLORS = {
  today: "#f59e0b",
  soon: "#10b981",
  upcoming: "var(--primary-text-color, #e2e8f0)",
};

class LifeEventsCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  setConfig(config) {
    this._config = {
      title: config.title || "Life Events",
      max_events: config.max_events || 10,
      show_types: config.show_types || ["birthday", "anniversary", "custom"],
      show_past_days: config.show_past_days || 0,
    };
  }

  _getEvents() {
    if (!this._hass) return [];

    const events = [];
    const states = this._hass.states;

    for (const entityId of Object.keys(states)) {
      if (!entityId.startsWith("sensor.life_events_")) continue;

      const state = states[entityId];
      const attrs = state.attributes || {};
      const daysUntil = parseInt(state.state, 10);

      if (isNaN(daysUntil)) continue;
      if (!this._config.show_types.includes(attrs.event_type)) continue;
      if (daysUntil < -this._config.show_past_days) continue;

      events.push({
        entity_id: entityId,
        name: attrs.name || entityId,
        days_until: daysUntil,
        next_date: attrs.next_date,
        years_at_next: attrs.years_at_next,
        event_type: attrs.event_type || "custom",
        event_label: attrs.event_label || "Event",
        year_unknown: attrs.year_unknown || false,
        icon: attrs.icon,
      });
    }

    return events
      .sort((a, b) => a.days_until - b.days_until)
      .slice(0, this._config.max_events);
  }

  _formatDate(dateStr) {
    if (!dateStr) return "";
    try {
      const d = new Date(dateStr + "T00:00:00");
      return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
    } catch {
      return dateStr;
    }
  }

  _urgencyLabel(days) {
    if (days === 0) return { label: "Today! 🎉", color: URGENCY_COLORS.today };
    if (days === 1) return { label: "Tomorrow", color: URGENCY_COLORS.soon };
    if (days <= 7) return { label: `In ${days} days`, color: URGENCY_COLORS.soon };
    return { label: `In ${days} days`, color: URGENCY_COLORS.upcoming };
  }

  _yearsLabel(event) {
    if (event.year_unknown || event.years_at_next == null) return "";
    const n = event.years_at_next;
    if (event.event_type === "birthday") return `Turning ${n}`;
    if (event.event_type === "anniversary") return `${n} years`;
    return `${n}`;
  }

  _render() {
    const events = this._getEvents();
    const root = this.shadowRoot;

    root.innerHTML = `
      <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=DM+Serif+Display&display=swap');

        :host {
          display: block;
          font-family: 'DM Sans', sans-serif;
        }

        .card {
          overflow: hidden;
        }

        .header {
          padding: 20px 20px 12px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          border-bottom: 1px solid var(--divider-color, rgba(0,0,0,0.08));
        }

        .header-title {
          font-family: 'DM Serif Display', serif;
          font-size: 1.2rem;
          color: var(--primary-text-color);
          letter-spacing: 0.01em;
        }

        .header-count {
          font-size: 0.75rem;
          color: var(--secondary-text-color);
          background: var(--secondary-background-color, rgba(0,0,0,0.06));
          padding: 3px 10px;
          border-radius: 20px;
        }

        .event-list {
          list-style: none;
          margin: 0;
          padding: 8px 0;
        }

        .event-item {
          display: grid;
          grid-template-columns: 44px 1fr auto;
          align-items: center;
          gap: 12px;
          padding: 10px 16px;
          transition: background 0.15s ease;
          cursor: default;
          border-bottom: 1px solid var(--divider-color, rgba(0,0,0,0.06));
        }

        .event-item:last-child {
          border-bottom: none;
        }

        .event-item:hover {
          background: var(--secondary-background-color, rgba(0,0,0,0.04));
        }

        .event-item.today {
          background: rgba(245, 158, 11, 0.08);
          border-left: 3px solid #f59e0b;
          padding-left: 13px;
        }

        .event-item.soon {
          border-left: 3px solid #10b981;
          padding-left: 13px;
        }

        .event-emoji-wrap {
          width: 44px;
          height: 44px;
          border-radius: 12px;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 1.5rem;
          flex-shrink: 0;
        }

        .event-info {
          min-width: 0;
        }

        .event-name {
          font-size: 0.95rem;
          font-weight: 600;
          color: var(--primary-text-color);
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .event-meta {
          display: flex;
          gap: 8px;
          align-items: center;
          margin-top: 2px;
        }

        .event-type-badge {
          font-size: 0.67rem;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.07em;
          padding: 2px 7px;
          border-radius: 6px;
          opacity: 0.85;
        }

        .event-years {
          font-size: 0.75rem;
          color: var(--secondary-text-color);
        }

        .event-right {
          text-align: right;
          flex-shrink: 0;
        }

        .event-days {
          font-size: 0.85rem;
          font-weight: 600;
        }

        .event-date {
          font-size: 0.72rem;
          color: var(--secondary-text-color);
          margin-top: 1px;
        }

        .empty {
          padding: 32px 20px;
          text-align: center;
          color: var(--secondary-text-color);
          font-size: 0.9rem;
        }

        .empty-icon {
          font-size: 2.5rem;
          margin-bottom: 8px;
          display: block;
        }
      </style>

      <ha-card class="card">
        <div class="header">
          <div class="header-title">${this._config.title}</div>
          <div class="header-count">${events.length} event${events.length !== 1 ? "s" : ""}</div>
        </div>

        ${
          events.length === 0
            ? `<div class="empty">
                <span class="empty-icon">🗓️</span>
                No upcoming events.<br>Add events via the integration settings.
               </div>`
            : `<ul class="event-list">
                ${events.map((ev) => this._renderEvent(ev)).join("")}
               </ul>`
        }
      </ha-card>
    `;
  }

  _renderEvent(ev) {
    const { label: urgencyLabel, color: urgencyColor } = this._urgencyLabel(ev.days_until);
    const typeColor = EVENT_COLORS[ev.event_type] || EVENT_COLORS.custom;
    const emoji = EVENT_ICONS[ev.event_type] || "⭐";
    const yearsLabel = this._yearsLabel(ev);
    const dateFormatted = this._formatDate(ev.next_date);

    let itemClass = "event-item";
    if (ev.days_until === 0) itemClass += " today";
    else if (ev.days_until <= 7) itemClass += " soon";

    return `
      <li class="${itemClass}">
        <div class="event-emoji-wrap" style="background: ${typeColor}18;">
          ${emoji}
        </div>
        <div class="event-info">
          <div class="event-name">${this._escapeHtml(ev.name)}</div>
          <div class="event-meta">
            <span class="event-type-badge" style="background: ${typeColor}22; color: ${typeColor};">
              ${this._escapeHtml(ev.event_label)}
            </span>
            ${yearsLabel ? `<span class="event-years">${this._escapeHtml(yearsLabel)}</span>` : ""}
          </div>
        </div>
        <div class="event-right">
          <div class="event-days" style="color: ${urgencyColor};">${urgencyLabel}</div>
          ${dateFormatted ? `<div class="event-date">${dateFormatted}</div>` : ""}
        </div>
      </li>
    `;
  }

  _escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  getCardSize() {
    return Math.max(2, Math.ceil((this._getEvents().length * 0.6) + 1));
  }

  static getConfigElement() {
    return document.createElement("life-events-card-editor");
  }

  static getStubConfig() {
    return {
      title: "Life Events",
      max_events: 10,
      show_types: ["birthday", "anniversary", "custom"],
    };
  }
}

// ── Visual editor (shown in Lovelace UI card picker) ──────────────────────

class LifeEventsCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
  }

  setConfig(config) {
    this._config = config;
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
  }

  _render() {
    const c = this._config || {};
    this.shadowRoot.innerHTML = `
      <style>
        .editor { padding: 16px; display: flex; flex-direction: column; gap: 12px; }
        label { font-size: 0.85rem; color: var(--secondary-text-color); display: block; margin-bottom: 4px; }
        input, select { width: 100%; padding: 8px; border-radius: 6px; border: 1px solid var(--divider-color); background: var(--card-background-color); color: var(--primary-text-color); font-size: 0.9rem; box-sizing: border-box; }
        .field { }
      </style>
      <div class="editor">
        <div class="field">
          <label>Card title</label>
          <input id="title" type="text" value="${c.title || "Life Events"}" />
        </div>
        <div class="field">
          <label>Max events to show</label>
          <input id="max_events" type="number" min="1" max="50" value="${c.max_events || 10}" />
        </div>
      </div>
    `;

    this.shadowRoot.querySelector("#title").addEventListener("change", (e) => {
      this._fireChange({ ...this._config, title: e.target.value });
    });
    this.shadowRoot.querySelector("#max_events").addEventListener("change", (e) => {
      this._fireChange({ ...this._config, max_events: parseInt(e.target.value, 10) });
    });
  }

  _fireChange(config) {
    this.dispatchEvent(new CustomEvent("config-changed", { detail: { config } }));
  }
}

// ── Registration ───────────────────────────────────────────────────────────

customElements.define("life-events-card", LifeEventsCard);
customElements.define("life-events-card-editor", LifeEventsCardEditor);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "life-events-card",
  name: "Life Events Card",
  description: "Shows upcoming birthdays, anniversaries, and custom events from the Life Events integration.",
  preview: true,
  documentationURL: "https://github.com/calebgab/ha-life-events",
});
