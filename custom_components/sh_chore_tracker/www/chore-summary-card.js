const DOMAIN = "sh_chore_tracker";
const DEFAULT_SNOOZE_DAYS = 3;

const ACTION_LABELS = {
  skip_chore: "Skip",
  complete_chore: "Complete",
  restore_chore: "Restore",
  reset_next_due_date: "Reset",
  snooze_chore: "Snooze",
};

class ShChoreSummaryCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._snoozeDaysTouched = false;
    this._pending = false;
  }

  setConfig(config) {
    if (!config || typeof config.entity !== "string" || !config.entity.startsWith("sensor.")) {
      throw new Error("Choose a chore sensor entity.");
    }

    if (this._config?.entity !== config.entity) {
      this._snoozeDaysTouched = false;
    }
    this._config = config;
    this._build();
    this._update();
  }

  set hass(hass) {
    this._hass = hass;
    this._update();
  }

  getCardSize() {
    return 8;
  }

  getGridOptions() {
    return { columns: 6, rows: "auto", min_rows: 4 };
  }

  _build() {
    if (this._card) {
      return;
    }

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          color: var(--primary-text-color);
        }

        ha-card {
          box-sizing: border-box;
          height: 100%;
          padding: 20px;
        }

        .header {
          align-items: flex-start;
          display: flex;
          gap: 12px;
          justify-content: space-between;
        }

        .title {
          font-size: 20px;
          font-weight: 600;
          line-height: 1.3;
          margin: 0;
          overflow-wrap: anywhere;
        }

        .status {
          background: var(--secondary-background-color);
          border-radius: 4px;
          color: var(--secondary-text-color);
          flex: 0 0 auto;
          font-size: 12px;
          line-height: 1.4;
          padding: 4px 8px;
          text-transform: capitalize;
        }

        .due {
          color: var(--secondary-text-color);
          margin: 8px 0 0;
        }

        .description {
          color: var(--secondary-text-color);
          margin: 8px 0 0;
          overflow-wrap: anywhere;
        }

        .actions {
          display: grid;
          gap: 8px;
          grid-template-columns: repeat(2, minmax(0, 1fr));
          margin-top: 20px;
        }

        button {
          background: var(--secondary-background-color);
          border: 1px solid var(--divider-color);
          border-radius: 4px;
          color: var(--primary-text-color);
          cursor: pointer;
          font: inherit;
          font-weight: 500;
          min-height: 40px;
          padding: 8px 12px;
        }

        button.primary {
          background: var(--primary-color);
          border-color: var(--primary-color);
          color: var(--text-primary-color, #fff);
        }

        button:hover:not(:disabled) {
          filter: brightness(0.94);
        }

        button:focus-visible,
        input:focus-visible {
          outline: 2px solid var(--primary-color);
          outline-offset: 2px;
        }

        button:disabled,
        input:disabled {
          cursor: not-allowed;
          opacity: 0.55;
        }

        .snooze {
          border-top: 1px solid var(--divider-color);
          margin-top: 16px;
          padding-top: 16px;
        }

        label {
          display: block;
          font-size: 14px;
          font-weight: 500;
          margin-bottom: 8px;
        }

        .snooze-control {
          display: grid;
          gap: 8px;
          grid-template-columns: minmax(0, 1fr) auto;
        }

        input {
          background: var(--card-background-color, var(--primary-background-color));
          border: 1px solid var(--divider-color);
          border-radius: 4px;
          box-sizing: border-box;
          color: var(--primary-text-color);
          font: inherit;
          min-width: 0;
          padding: 8px 10px;
          width: 100%;
        }

        .feedback {
          color: var(--secondary-text-color);
          min-height: 1.3em;
          margin: 12px 0 0;
        }

        .feedback[data-error="true"] {
          color: var(--error-color);
        }
      </style>
      <ha-card>
        <section class="content" aria-live="polite">
          <header class="header">
            <h2 class="title"></h2>
            <span class="status"></span>
          </header>
          <p class="due"></p>
          <p class="description" hidden></p>
          <div class="actions" aria-label="Chore actions">
            <button type="button" data-action="skip_chore">Skip</button>
            <button type="button" class="primary" data-action="complete_chore">Complete</button>
            <button type="button" data-action="restore_chore">Restore</button>
            <button type="button" data-action="reset_next_due_date">Reset</button>
          </div>
          <form class="snooze">
            <label for="snooze-days">Snooze days</label>
            <div class="snooze-control">
              <input
                id="snooze-days"
                type="number"
                min="1"
                max="365"
                step="1"
                required
                inputmode="numeric"
              >
              <button type="submit" class="primary">Snooze</button>
            </div>
          </form>
          <p class="feedback" role="status" aria-live="polite"></p>
        </section>
      </ha-card>
    `;

    this._card = this.shadowRoot.querySelector("ha-card");
    this._title = this.shadowRoot.querySelector(".title");
    this._status = this.shadowRoot.querySelector(".status");
    this._due = this.shadowRoot.querySelector(".due");
    this._description = this.shadowRoot.querySelector(".description");
    this._feedback = this.shadowRoot.querySelector(".feedback");
    this._daysInput = this.shadowRoot.querySelector("#snooze-days");
    this._buttons = [...this.shadowRoot.querySelectorAll("button")];

    for (const button of this.shadowRoot.querySelectorAll("[data-action]")) {
      button.addEventListener("click", () => this._runAction(button.dataset.action));
    }

    this.shadowRoot.querySelector(".snooze").addEventListener("submit", (event) => {
      event.preventDefault();
      const days = this._daysInput.valueAsNumber;
      if (!this._daysInput.reportValidity() || !Number.isInteger(days)) {
        return;
      }
      this._runAction("snooze_chore", { days });
    });

    this._daysInput.addEventListener("input", () => {
      this._snoozeDaysTouched = true;
    });
  }

  _update() {
    if (!this._config || !this._hass) {
      return;
    }

    const entity = this._hass.states[this._config.entity];
    const attributes = entity?.attributes ?? {};
    this._title.textContent =
      attributes.friendly_name || this._config.name || this._config.entity;
    this._status.textContent = attributes.status || "Unavailable";
    this._status.dataset.status = attributes.status || "unavailable";
    this._due.textContent = this._formatDue(attributes.days_until_due, attributes.next_due_date);
    this._description.textContent = attributes.description || "";
    this._description.hidden = !attributes.description;

    if (!this._snoozeDaysTouched) {
      const configuredDefault = Number(attributes.default_snooze_days);
      const defaultDays = Number.isInteger(configuredDefault)
        ? configuredDefault
        : DEFAULT_SNOOZE_DAYS;
      this._daysInput.value = String(defaultDays);
    }

    const unavailable = !entity;
    this._card.setAttribute("aria-busy", String(this._pending));
    for (const button of this._buttons) {
      button.disabled = unavailable || this._pending;
    }
    this._daysInput.disabled = unavailable || this._pending;
  }

  _formatDue(daysUntilDue, nextDueDate) {
    const days = Number(daysUntilDue);
    let relative;
    if (!Number.isInteger(days)) {
      relative = "Due date unavailable";
    } else if (days < 0) {
      const overdueDays = Math.abs(days);
      relative = `${overdueDays} day${overdueDays === 1 ? "" : "s"} overdue`;
    } else if (days === 0) {
      relative = "Due today";
    } else {
      relative = `Due in ${days} day${days === 1 ? "" : "s"}`;
    }

    const dateMatch = typeof nextDueDate === "string" && nextDueDate.match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (!dateMatch) {
      return relative;
    }

    const dueDate = new Date(
      Number(dateMatch[1]),
      Number(dateMatch[2]) - 1,
      Number(dateMatch[3]),
    );
    return `${relative} - ${dueDate.toLocaleDateString()}`;
  }

  async _runAction(service, extraData = {}) {
    if (this._pending || !this._hass || !this._hass.states[this._config.entity]) {
      return;
    }

    this._pending = true;
    this._feedback.dataset.error = "false";
    this._feedback.textContent = "Working...";
    this._update();

    try {
      await this._hass.callService(DOMAIN, service, {
        entity_id: this._config.entity,
        ...extraData,
      });
      this._feedback.textContent = `${ACTION_LABELS[service]} action complete.`;
    } catch (error) {
      this._feedback.dataset.error = "true";
      this._feedback.textContent = error?.message || "The chore action failed.";
    } finally {
      this._pending = false;
      this._update();
    }
  }
}

customElements.define("sh-chore-summary-card", ShChoreSummaryCard);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "sh-chore-summary-card",
  name: "Chore Summary",
  description: "A chore summary with schedule actions.",
});