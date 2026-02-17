/**
 * Application initialization and event handlers
 */

import { ACGMEForm } from "./acgme.js";
import { DOM, STATUS_TYPES } from "./constants.js";
import { Excel } from "./excel.js";
import { Form } from "./form.js";
import { Navigation } from "./navigation.js";
import { Settings } from "./settings.js";
import { State } from "./state.js";
import { Storage } from "./storage.js";
import { UI } from "./ui.js";

const activeStyles = [
  "bg-orange-500",
  "hover:bg-orange-600",
  "border-orange-500",
  "beast-mode-active",
];

const beastModeStyles = {
  paused: ["bg-blue-500", "hover:bg-blue-600", "border-blue-500"],
  inactive: ["bg-red-500", "hover:bg-red-600", "border-red-500"],
};

const FileUpload = {
  async handleFile(file) {
    if (!file) {
      return;
    }

    UI.get(DOM.fileName).textContent = file.name;

    try {
      const result = await Excel.parseFile(file);
      const { cases, mappingResult } = result;

      if (cases.length === 0) {
        UI.showStatus("No valid cases found in file", "error");
        return;
      }

      State.setCases(cases);
      Navigation.showCaseView();
      Form.populate(State.getCurrentCase());
      Navigation.update();
      Storage.saveState();

      // Show mapping status
      UI.showMappingStatus(mappingResult);

      UI.showStatus(`Loaded ${cases.length} cases`, "success");
    } catch (error) {
      UI.showStatus(`Error parsing file: ${error.message}`, "error");
      console.error(error);
    }
  },

  openFilePicker() {
    UI.get(DOM.fileInput).click();
  },
};

const BeastMode = {
  isActive: false,
  shouldStop: false,
  isPaused: false,
  currentIndex: 0,
  resumeCallback: null,

  disableActionButtons() {
    UI.get(DOM.skipBtn).disabled = true;
    UI.get(DOM.fillBtn).disabled = true;
    UI.get(DOM.fillSubmitBtn).disabled = true;
  },

  enableActionButtons() {
    UI.get(DOM.skipBtn).disabled = false;
    UI.get(DOM.fillBtn).disabled = false;
    UI.get(DOM.fillSubmitBtn).disabled = false;
  },
  async start() {
    if (this.isActive && !this.isPaused) {
      return;
    }

    // If resuming from pause, just resume
    if (this.isPaused) {
      this.resume();
      return;
    }

    // Starting fresh
    this.isActive = true;
    this.shouldStop = false;
    this.isPaused = false;
    this.currentIndex = 0;

    // Update UI
    const btn = UI.get(DOM.beastModeBtn);
    const text = UI.get(DOM.beastModeText);
    btn.classList.remove(...beastModeStyles.inactive);
    btn.classList.add(...activeStyles);
    text.textContent = "STOP BEAST MODE";

    this.disableActionButtons();

    UI.showStatus("BEAST MODE ACTIVATED - Processing cases...", "info");

    try {
      await this.processAllPending();
    } catch (error) {
      console.error("BEAST mode error:", error);
      UI.showStatus(`BEAST mode error: ${error.message}`, "error");
    } finally {
      if (!this.isPaused) {
        this.stop();
      }
    }
  },

  pause(message) {
    this.isPaused = true;

    // Update UI to show paused state
    const btn = UI.get(DOM.beastModeBtn);
    const text = UI.get(DOM.beastModeText);
    btn.classList.remove(...activeStyles);
    btn.classList.add(...beastModeStyles.paused);
    text.textContent = "CONTINUE BEAST MODE";

    // Re-enable action buttons so user can fix things
    this.enableActionButtons();

    UI.showStatus(message || "BEAST mode paused", "info");
  },

  resume() {
    this.isPaused = false;

    // Update UI back to active state
    const btn = UI.get(DOM.beastModeBtn);
    const text = UI.get(DOM.beastModeText);
    btn.classList.remove(...beastModeStyles.paused);
    btn.classList.add(...activeStyles);
    text.textContent = "STOP BEAST MODE";

    // Disable action buttons again
    this.disableActionButtons();

    UI.showStatus("BEAST MODE RESUMED - Processing cases...", "info");

    // Call the resume callback if it exists
    if (this.resumeCallback) {
      this.resumeCallback();
      this.resumeCallback = null;
    }
  },

  stop() {
    this.isActive = false;
    this.shouldStop = true;
    this.isPaused = false;
    this.resumeCallback = null;

    // Update UI
    const btn = UI.get(DOM.beastModeBtn);
    const text = UI.get(DOM.beastModeText);
    btn.classList.remove(...activeStyles, ...beastModeStyles.paused);
    btn.classList.add(...beastModeStyles.inactive);
    text.textContent = "START BEAST MODE";

    // Re-enable action buttons
    this.enableActionButtons();
  },

  async processAllPending() {
    const totalCases = State.cases.length;
    let processed = 0;

    // Start from currentIndex (for resuming) or 0
    const startIndex = this.currentIndex || 0;

    for (let i = startIndex; i < totalCases; i++) {
      this.currentIndex = i;

      if (this.shouldStop) {
        UI.showStatus(
          `BEAST mode stopped. Processed ${processed} cases.`,
          "info",
        );
        return;
      }

      // Wait if paused
      if (this.isPaused) {
        await new Promise((resolve) => {
          this.resumeCallback = resolve;
        });
      }

      // Skip non-pending cases
      if (State.getCaseStatus(i) !== STATUS_TYPES.pending) {
        continue;
      }

      // Navigate to this case
      Navigation.goToCase(i);

      // Wait for page to fully load before starting fill/submit process
      await new Promise((resolve) => setTimeout(resolve, 1500)); // 1.5 second delay for page load

      // Validate - pause if validation fails
      const validation = Form.validate();
      if (!validation.isValid) {
        UI.showValidation(validation);
        this.pause(
          `BEAST mode paused at case ${i + 1}/${totalCases}. Please complete required fields (${validation.missing.join(", ")}) and click CONTINUE.`,
        );

        // Wait for user to fix and continue
        await new Promise((resolve) => {
          this.resumeCallback = resolve;
        });

        // Re-validate after user fixes
        const revalidation = Form.validate();
        if (!revalidation.isValid) {
          // Still invalid, pause again
          i--; // Retry this case
          continue;
        }
      }

      try {
        // Fill and submit the case
        UI.showStatus(`Processing case ${i + 1}/${totalCases}...`, "info");

        const result = await ACGMEForm.fill(true);

        if (result?.success && result?.submitted) {
          processed++;
          UI.showStatus(
            `Case ${i + 1}/${totalCases} submitted! (${processed} total)`,
            "success",
          );
        } else {
          console.warn(`Case ${i + 1} failed to submit:`, result);
          // Pause on submission failure
          this.pause(
            `Case ${i + 1} failed to submit. Check the ACGME form and click CONTINUE to retry or STOP to end.`,
          );
          await new Promise((resolve) => {
            this.resumeCallback = resolve;
          });
          i--; // Retry this case
          continue;
        }

        // Random delay between 0.5-1 second
        const delay = Math.random() * 500 + 500; // 500-1000ms
        await new Promise((resolve) => setTimeout(resolve, delay));
      } catch (error) {
        console.error(`Error processing case ${i + 1}:`, error);
        this.pause(
          `Error processing case ${i + 1}: ${error.message}. Click CONTINUE to retry or STOP to end.`,
        );
        await new Promise((resolve) => {
          this.resumeCallback = resolve;
        });
        i--; // Retry this case
      }
    }

    // Reset current index
    this.currentIndex = 0;

    // Find next pending case or finish
    const nextPending = State.findNextPending(-1);
    if (nextPending === null) {
      UI.showStatus(
        `BEAST mode complete! Processed ${processed} cases. All done!`,
        "success",
      );
    } else {
      Navigation.goToCase(nextPending);
      UI.showStatus(
        `Processed ${processed} cases! ${State.getStats().pending} cases remaining.`,
        "success",
      );
    }
  },
};

const Session = {
  async clear() {
    if (
      !confirm("Clear all loaded cases and progress? This cannot be undone.")
    ) {
      return;
    }

    try {
      // Clear storage first
      await Storage.clearState();

      // Reset the file input completely
      const fileInput = UI.get(DOM.fileInput);
      fileInput.value = "";
      fileInput.type = "text";
      fileInput.type = "file";

      // Reset UI elements
      UI.get(DOM.fileName).textContent = "";

      // Clear form fields if they exist
      const formFields = [
        DOM.caseId,
        DOM.date,
        DOM.attending,
        DOM.ageCategory,
        DOM.asa,
        DOM.anesthesia,
        DOM.procedureCategory,
        DOM.comments,
      ];

      formFields.forEach((fieldId) => {
        const field = document.getElementById(fieldId);
        if (field) {
          field.value = "";
        }
      });

      // Clear checkboxes and radios
      document
        .querySelectorAll('input[type="checkbox"][name="airway"]')
        .forEach((cb) => {
          cb.checked = false;
        });
      document
        .querySelectorAll('input[type="checkbox"][name="vascular"]')
        .forEach((cb) => {
          cb.checked = false;
        });
      document
        .querySelectorAll('input[type="checkbox"][name="monitoring"]')
        .forEach((cb) => {
          cb.checked = false;
        });
      document
        .querySelectorAll('input[type="radio"][name="difficultAirway"]')
        .forEach((radio) => {
          radio.checked = radio.value === "";
        });
      document
        .querySelectorAll(
          'input[type="radio"][name="lifeThreateningPathology"]',
        )
        .forEach((radio) => {
          radio.checked = radio.value === "";
        });

      // Reset navigation counters
      const navElements = [
        DOM.currentIndex,
        DOM.totalCount,
        DOM.currentIndexBottom,
        DOM.totalCountBottom,
        DOM.pendingCount,
        DOM.submittedCount,
        DOM.skippedCount,
      ];

      navElements.forEach((elementId) => {
        const element = document.getElementById(elementId);
        if (element) {
          element.textContent = "0";
        }
      });

      // Clear jump dropdown
      const jumpSelect = UI.get(DOM.caseJump);
      if (jumpSelect) {
        jumpSelect.innerHTML = "";
      }

      // Hide validation summary
      const validationSummary = UI.get(DOM.validationSummary);
      if (validationSummary) {
        validationSummary.classList.add("hidden");
      }

      // Reset button states
      const fillSubmitBtn = UI.get(DOM.fillSubmitBtn);
      if (fillSubmitBtn) {
        fillSubmitBtn.disabled = false;
      }

      // Hide case preview and navigation sections
      UI.hideSection(DOM.navSection);
      UI.hideSection(DOM.previewSection);

      // Show upload section
      UI.showSection(DOM.uploadSection);

      // Clear any status messages
      UI.hideStatus();

      // Show success message after a brief delay
      setTimeout(() => {
        UI.showStatus("Session cleared - ready for new file", "success");
      }, 100);
    } catch (error) {
      console.error("Error clearing session:", error);
      UI.showStatus("Error clearing session", "error");
    }
  },

  async restore() {
    const restored = await Storage.loadState();
    if (restored) {
      Navigation.showCaseView();
      Form.populate(State.getCurrentCase());
      Navigation.update();
      UI.showStatus(
        `Restored ${State.cases.length} cases from previous session`,
        "info",
      );
    }
  },
};

const EventHandlers = {
  register() {
    const addListener = (id, event, handler) => {
      const element = UI.get(id);
      if (!element) {
        if (process.env.NODE_ENV === "development") {
          console.error(`Element not found: ${id}`);
        }
        return;
      }
      element.addEventListener(event, (...args) => {
        if (process.env.NODE_ENV === "development") {
          console.log(`Button clicked: ${id}`);
        }
        try {
          handler(...args);
        } catch (error) {
          console.error(`Error in ${id} handler:`, error);
        }
      });
    };

    // Upload
    addListener(DOM.uploadBtn, "click", () => FileUpload.openFilePicker());
    addListener(DOM.fileInput, "change", (e) =>
      FileUpload.handleFile(e.target.files[0]),
    );

    // Navigation
    addListener(DOM.prevBtn, "click", () =>
      Navigation.goToCase(State.currentIndex - 1),
    );
    addListener(DOM.nextBtn, "click", () =>
      Navigation.goToCase(State.currentIndex + 1),
    );
    addListener(DOM.prevBtnBottom, "click", () =>
      Navigation.goToCase(State.currentIndex - 1),
    );
    addListener(DOM.nextBtnBottom, "click", () =>
      Navigation.goToCase(State.currentIndex + 1),
    );
    addListener(DOM.caseJump, "change", (e) =>
      Navigation.goToCase(Number.parseInt(e.target.value, 10)),
    );
    addListener(DOM.filterPending, "change", () => Navigation.update());

    // Actions
    addListener(DOM.skipBtn, "click", () => {
      State.setCaseStatus(State.currentIndex, STATUS_TYPES.skipped);
      Navigation.update();
      Storage.saveState();
      Navigation.goToNextPending();
    });

    addListener(DOM.fillBtn, "click", async () => {
      const validation = Form.validate();
      if (!validation.isValid) {
        UI.showValidation(validation);
        UI.showStatus(
          "Please complete required fields before filling",
          "error",
        );
        return;
      }

      if (validation.hasWarnings) {
        UI.showValidation(validation);
      }

      UI.get(DOM.fillBtn).disabled = true;
      try {
        await ACGMEForm.fill(false);
      } finally {
        UI.get(DOM.fillBtn).disabled = false;
      }
    });

    addListener(DOM.fillSubmitBtn, "click", async () => {
      const validation = Form.validate();

      // Show validation but don't block submission
      if (!validation.isValid || validation.hasWarnings) {
        UI.showValidation(validation);
        if (!validation.isValid) {
          UI.showStatus(
            "Warning: Some required fields are missing. Proceeding anyway.",
            "info",
          );
        }
      }

      const submitBtn = UI.get(DOM.fillSubmitBtn);
      submitBtn.disabled = true;
      try {
        await ACGMEForm.fill(true);
      } finally {
        // Always re-enable the button after submission attempt
        submitBtn.disabled = false;
      }
    });

    // BEAST Mode
    addListener(DOM.beastModeBtn, "click", () => {
      if (BeastMode.isPaused) {
        // Resume from pause
        BeastMode.start();
      } else if (BeastMode.isActive) {
        // Stop active BEAST mode
        BeastMode.stop();
      } else {
        // Start fresh
        BeastMode.start();
      }
    });

    // Settings
    addListener(DOM.settingsToggle, "click", () => Settings.toggle());
    addListener(DOM.settingSubmitDelay, "input", (e) => {
      UI.get(DOM.submitDelayValue).textContent = `${e.target.value}s`;
    });
    addListener(DOM.saveSettingsBtn, "click", () => Settings.save());
    addListener(DOM.clearSessionBtn, "click", () => Session.clear());

    // ASA field - auto-check 5E pathology
    addListener(DOM.asa, "change", (e) => {
      const isFiveE = e.target.value === "5E";
      const currentPathology = Form.getRadioGroup("lifeThreateningPathology");

      if (State.settings.auto5EPathology && isFiveE && !currentPathology) {
        Form.setRadioGroup("lifeThreateningPathology", "Non-Trauma");
      }

      // Real-time validation
      const validation = Form.validate();
      UI.showValidation(validation);
    });

    // Real-time validation for other required fields
    const requiredFields = [
      DOM.attending,
      DOM.anesthesia,
      DOM.procedureCategory,
    ];
    requiredFields.forEach((fieldId) => {
      addListener(fieldId, "change", () => {
        const validation = Form.validate();
        UI.showValidation(validation);
      });
    });

    // Keyboard shortcuts
    document.addEventListener("keydown", (e) => {
      if (State.cases.length === 0) {
        return;
      }

      const isInputFocused = e.target.matches("input, textarea, select");

      if (e.key === "ArrowLeft" && !isInputFocused) {
        e.preventDefault();
        Navigation.goToCase(State.currentIndex - 1);
      } else if (e.key === "ArrowRight" && !isInputFocused) {
        e.preventDefault();
        Navigation.goToCase(State.currentIndex + 1);
      }
    });

    if (process.env.NODE_ENV === "development") {
      console.log("Event handlers registered successfully");
    }
  },
};

const App = {
  async init() {
    try {
      await Storage.loadSettings();
      Settings.applyToUI();
      await Session.restore();
      EventHandlers.register();
      if (process.env.NODE_ENV === "development") {
        console.log("ACGME Case Submitter initialized successfully");
      }
    } catch (error) {
      console.error("Error initializing app:", error);
    }
  },
};

// Handle both DOMContentLoaded and already-loaded cases
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => App.init());
} else {
  // DOM already loaded
  App.init();
}
