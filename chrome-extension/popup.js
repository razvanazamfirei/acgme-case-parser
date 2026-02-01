// State
let cases = [];
let currentIndex = 0;
let caseStatuses = {}; // { index: 'pending' | 'submitted' | 'skipped' }
let settings = {
  defaultInstitution: "",
  defaultAttending: "",
  submitDelay: 0.5,
  cardiacAutoFill: true,
};
let pendingSubmission = false;

// Expected column headers from the Python tool output
const EXPECTED_COLUMNS = [
  "Case ID",
  "Case Date",
  "Supervisor",
  "Age",
  "Original Procedure",
  "ASA Physical Status",
  "Anesthesia Type",
  "Airway Management",
  "Procedure Category",
  "Specialized Vascular Access",
  "Specialized Monitoring Techniques",
];

// Storage keys
const STORAGE_KEYS = {
  cases: "acgme_cases",
  currentIndex: "acgme_currentIndex",
  caseStatuses: "acgme_caseStatuses",
  settings: "acgme_settings",
};

// Load state from chrome.storage
async function loadState() {
  try {
    const result = await chrome.storage.local.get([
      STORAGE_KEYS.cases,
      STORAGE_KEYS.currentIndex,
      STORAGE_KEYS.caseStatuses,
    ]);

    if (result[STORAGE_KEYS.cases] && result[STORAGE_KEYS.cases].length > 0) {
      cases = result[STORAGE_KEYS.cases];
      currentIndex = result[STORAGE_KEYS.currentIndex] || 0;
      caseStatuses = result[STORAGE_KEYS.caseStatuses] || {};

      // Ensure currentIndex is valid
      if (currentIndex >= cases.length) {
        currentIndex = 0;
      }

      showCases();
      populateForm(cases[currentIndex]);
      updateNavigation();
      showStatus(
        `Restored ${cases.length} cases from previous session`,
        "info",
      );
    }
  } catch (error) {
    console.error("Error loading state:", error);
  }
}

// Save state to chrome.storage
async function saveState() {
  try {
    await chrome.storage.local.set({
      [STORAGE_KEYS.cases]: cases,
      [STORAGE_KEYS.currentIndex]: currentIndex,
      [STORAGE_KEYS.caseStatuses]: caseStatuses,
    });
  } catch (error) {
    console.error("Error saving state:", error);
  }
}

// Load settings from chrome.storage.sync
async function loadSettings() {
  try {
    const result = await chrome.storage.sync.get(STORAGE_KEYS.settings);
    if (result[STORAGE_KEYS.settings]) {
      settings = { ...settings, ...result[STORAGE_KEYS.settings] };
    }
    applySettingsToUI();
  } catch (error) {
    console.error("Error loading settings:", error);
  }
}

// Save settings to chrome.storage.sync
async function saveSettings() {
  try {
    settings = {
      defaultInstitution: document.getElementById("settingInstitution").value,
      defaultAttending: document
        .getElementById("settingDefaultAttending")
        .value.trim(),
      submitDelay: parseFloat(
        document.getElementById("settingSubmitDelay").value,
      ),
      cardiacAutoFill: document.getElementById("settingCardiacAutoFill")
        .checked,
    };
    await chrome.storage.sync.set({ [STORAGE_KEYS.settings]: settings });
    showStatus("Settings saved", "success");
    document.getElementById("settingsSection").classList.add("hidden");
  } catch (error) {
    console.error("Error saving settings:", error);
    showStatus("Error saving settings", "error");
  }
}

// Apply loaded settings to UI
function applySettingsToUI() {
  document.getElementById("settingInstitution").value =
    settings.defaultInstitution || "";
  document.getElementById("settingDefaultAttending").value =
    settings.defaultAttending || "";
  document.getElementById("settingSubmitDelay").value = settings.submitDelay;
  document.getElementById("submitDelayValue").textContent =
    `${settings.submitDelay}s`;
  document.getElementById("settingCardiacAutoFill").checked =
    settings.cardiacAutoFill;
}

// Clear session data
async function clearSession() {
  try {
    await chrome.storage.local.remove([
      STORAGE_KEYS.cases,
      STORAGE_KEYS.currentIndex,
      STORAGE_KEYS.caseStatuses,
    ]);
    cases = [];
    currentIndex = 0;
    caseStatuses = {};

    document.getElementById("uploadSection").classList.remove("hidden");
    document.getElementById("navSection").classList.add("hidden");
    document.getElementById("previewSection").classList.add("hidden");
    document.getElementById("fileName").textContent = "";
    document.getElementById("fileInput").value = "";

    showStatus("Session cleared", "success");
  } catch (error) {
    console.error("Error clearing session:", error);
    showStatus("Error clearing session", "error");
  }
}

// Parse Excel file using SheetJS
function parseExcelFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = new Uint8Array(e.target.result);
        const workbook = XLSX.read(data, { type: "array" });
        const firstSheet = workbook.Sheets[workbook.SheetNames[0]];

        // Get raw data with headers
        const rows = XLSX.utils.sheet_to_json(firstSheet, { header: 1 });
        if (rows.length < 2) {
          reject(new Error("File has no data rows"));
          return;
        }

        // First row should be headers
        const headers = rows[0].map((h) => String(h || "").trim());

        // Map header names to indices
        const colIndex = {};
        EXPECTED_COLUMNS.forEach((col) => {
          const idx = headers.findIndex(
            (h) => h.toLowerCase() === col.toLowerCase(),
          );
          if (idx !== -1) {
            colIndex[col] = idx;
          }
        });

        // Parse data rows
        const parsed = [];
        for (let i = 1; i < rows.length; i++) {
          const row = rows[i];
          if (!row || row.length === 0) {
            continue;
          }

          const caseData = {
            caseId: getString(row, colIndex["Case ID"]),
            date: formatDate(row[colIndex["Case Date"]]),
            attending: getString(row, colIndex.Supervisor),
            ageCategory: getString(row, colIndex.Age),
            comments: getString(row, colIndex["Original Procedure"]),
            asa: getString(row, colIndex["ASA Physical Status"]),
            anesthesia: getString(row, colIndex["Anesthesia Type"]),
            airway: getString(row, colIndex["Airway Management"]),
            procedureCategory: getString(row, colIndex["Procedure Category"]),
            vascularAccess: getString(
              row,
              colIndex["Specialized Vascular Access"],
            ),
            monitoring: getString(
              row,
              colIndex["Specialized Monitoring Techniques"],
            ),
          };

          // Only add if we have a case ID
          if (caseData.caseId) {
            parsed.push(caseData);
          }
        }

        resolve(parsed);
      } catch (err) {
        reject(err);
      }
    };
    reader.onerror = () => reject(new Error("Failed to read file"));
    reader.readAsArrayBuffer(file);
  });
}

function getString(row, idx) {
  if (idx === undefined || idx === null) {
    return "";
  }
  const val = row[idx];
  if (val === null || val === undefined) {
    return "";
  }
  return String(val).trim();
}

function formatDate(val) {
  if (!val) {
    return "";
  }

  // If it's already a string in MM/DD/YYYY format
  if (typeof val === "string" && /^\d{1,2}\/\d{1,2}\/\d{4}$/.test(val)) {
    return val;
  }

  // Excel serial date number
  if (typeof val === "number") {
    const date = new Date((val - 25569) * 86400 * 1000);
    const month = date.getMonth() + 1;
    const day = date.getDate();
    const year = date.getFullYear();
    return `${month}/${day}/${year}`;
  }

  // Try parsing as date string
  const d = new Date(val);
  if (!Number.isNaN(d.getTime())) {
    return `${d.getMonth() + 1}/${d.getDate()}/${d.getFullYear()}`;
  }

  return String(val);
}

// UI Functions
function showStatus(msg, type) {
  const section = document.getElementById("statusSection");
  const message = document.getElementById("statusMessage");
  section.classList.remove("hidden");
  message.className = `status-message ${type}`;
  message.textContent = msg;

  if (type === "success" || type === "info") {
    setTimeout(() => {
      section.classList.add("hidden");
    }, 3000);
  }
}

function hideStatus() {
  document.getElementById("statusSection").classList.add("hidden");
}

function updateStats() {
  let pending = 0,
    submitted = 0,
    skipped = 0;
  for (let i = 0; i < cases.length; i++) {
    const status = caseStatuses[i] || "pending";
    if (status === "pending") {
      pending++;
    } else {
      if (status === "submitted") {
        submitted++;
      } else {
        if (status === "skipped") {
          skipped++;
        }
      }
    }
  }

  document.getElementById("pendingCount").textContent = pending.toString();
  document.getElementById("submittedCount").textContent = submitted.toString();
  document.getElementById("skippedCount").textContent = skipped.toString();
}

function updateNavigation() {
  document.getElementById("currentIndex").textContent = (
    currentIndex + 1
  ).toString();
  document.getElementById("totalCount").textContent = cases.length.toString();

  document.getElementById("prevBtn").disabled = currentIndex === 0;
  document.getElementById("nextBtn").disabled =
    currentIndex >= cases.length - 1;

  // Update jump dropdown
  const jumpSelect = document.getElementById("caseJump");
  const filterPending = document.getElementById("filterPending").checked;

  jumpSelect.innerHTML = "";
  for (let i = 0; i < cases.length; i++) {
    const status = caseStatuses[i] || "pending";
    if (filterPending && status !== "pending") {
      continue;
    }

    const opt = document.createElement("option");
    opt.value = i;
    opt.textContent = `${i + 1}. ${cases[i].caseId} (${status})`;
    if (i === currentIndex) {
      opt.selected = true;
    }
    jumpSelect.appendChild(opt);
  }

  updateStats();
}

function setSelectValue(selectId, value) {
  const select = document.getElementById(selectId);
  if (!select) {
    return;
  }
  if (!value) {
    select.value = "";
    return;
  }

  // Try exact match first
  if ([...select.options].some((opt) => opt.value === value)) {
    select.value = value;
    return;
  }

  // Try case-insensitive match
  const valueLower = value.toLowerCase();
  for (const opt of select.options) {
    if (opt.value.toLowerCase() === valueLower) {
      select.value = opt.value;
      return;
    }
  }

  // Try partial match (value starts with option or vice versa)
  for (const opt of select.options) {
    if (
      opt.value &&
      (valueLower.startsWith(opt.value.toLowerCase()) ||
        opt.value.toLowerCase().startsWith(valueLower))
    ) {
      select.value = opt.value;
      return;
    }
  }

  // No match found, leave empty
  select.value = "";
}

function setCheckboxGroup(name, valuesString) {
  // Uncheck all first
  document.querySelectorAll(`input[name="${name}"]`).forEach((cb) => {
    cb.checked = false;
  });

  if (!valuesString) {
    return;
  }

  // Parse semicolon-separated values
  const values = valuesString.split(";").map((v) => v.trim().toLowerCase());

  // Check matching checkboxes
  document.querySelectorAll(`input[name="${name}"]`).forEach((cb) => {
    const cbValue = cb.value.toLowerCase();
    if (
      values.some(
        (v) => v === cbValue || cbValue.includes(v) || v.includes(cbValue),
      )
    ) {
      cb.checked = true;
    }
  });
}

function getCheckboxGroup(name) {
  const checked = [];
  document.querySelectorAll(`input[name="${name}"]:checked`).forEach((cb) => {
    checked.push(cb.value);
  });
  return checked.join("; ");
}

function populateForm(caseData) {
  document.getElementById("caseId").value = caseData.caseId || "";
  document.getElementById("date").value = caseData.date || "";
  document.getElementById("attending").value = caseData.attending || "";
  document.getElementById("comments").value = caseData.comments || "";

  // Select fields - use smart matching
  setSelectValue("ageCategory", caseData.ageCategory);
  setSelectValue("asa", caseData.asa);
  setSelectValue("anesthesia", caseData.anesthesia);
  setSelectValue("procedureCategory", caseData.procedureCategory);

  // Checkbox groups
  setCheckboxGroup("airway", caseData.airway);
  setCheckboxGroup("vascular", caseData.vascularAccess);
  setCheckboxGroup("monitoring", caseData.monitoring);

  // Update status badge
  const status = caseStatuses[currentIndex] || "pending";
  const badge = document.getElementById("caseStatus");
  badge.className = `status-badge ${status}`;
  badge.textContent = status.charAt(0).toUpperCase() + status.slice(1);

  // Hide confirmation panel when navigating
  hideConfirmation();
}

function getFormData() {
  return {
    caseId: document.getElementById("caseId").value,
    date: document.getElementById("date").value,
    attending: document.getElementById("attending").value,
    ageCategory: document.getElementById("ageCategory").value,
    asa: document.getElementById("asa").value,
    anesthesia: document.getElementById("anesthesia").value,
    airway: getCheckboxGroup("airway"),
    procedureCategory: document.getElementById("procedureCategory").value,
    vascularAccess: getCheckboxGroup("vascular"),
    monitoring: getCheckboxGroup("monitoring"),
    comments: document.getElementById("comments").value,
    // Include settings for content script
    institution: settings.defaultInstitution,
    defaultAttending: settings.defaultAttending,
    cardiacAutoFill: settings.cardiacAutoFill,
  };
}

function showCases() {
  document.getElementById("uploadSection").classList.add("hidden");
  document.getElementById("navSection").classList.remove("hidden");
  document.getElementById("previewSection").classList.remove("hidden");
}

function goToCase(index) {
  if (index < 0 || index >= cases.length) {
    return;
  }
  currentIndex = index;
  populateForm(cases[currentIndex]);
  updateNavigation();
  hideStatus();
  saveState();
}

function goToNextPending() {
  for (let i = currentIndex + 1; i < cases.length; i++) {
    if ((caseStatuses[i] || "pending") === "pending") {
      goToCase(i);
      return;
    }
  }
  for (let i = 0; i < currentIndex; i++) {
    if ((caseStatuses[i] || "pending") === "pending") {
      goToCase(i);
      return;
    }
  }
  showStatus("All cases have been processed!", "success");
}

// Build confirmation summary HTML
function buildConfirmationSummary(caseData) {
  const items = [
    { label: "Case ID", value: caseData.caseId },
    { label: "Date", value: caseData.date },
    {
      label: "Attending",
      value: caseData.attending || settings.defaultAttending || "(not set)",
      warning: !caseData.attending && !settings.defaultAttending,
    },
    { label: "ASA", value: caseData.asa },
    { label: "Anesthesia", value: caseData.anesthesia },
    { label: "Procedure", value: caseData.procedureCategory || "Other" },
  ];

  return items
    .map((item) => {
      const valueClass = item.warning
        ? "summary-value warning"
        : "summary-value";
      return `<div class="summary-item"><span class="summary-label">${item.label}:</span><span class="${valueClass}">${item.value || "--"}</span></div>`;
    })
    .join("");
}

function showConfirmation() {
  const caseData = getFormData();
  document.getElementById("confirmationSummary").innerHTML =
    buildConfirmationSummary(caseData);
  document.getElementById("confirmationPanel").classList.remove("hidden");
  document.getElementById("fillSubmitBtn").disabled = true;
  pendingSubmission = true;
}

function hideConfirmation() {
  document.getElementById("confirmationPanel").classList.add("hidden");
  document.getElementById("fillSubmitBtn").disabled = false;
  pendingSubmission = false;
}

async function fillForm(andSubmit = false) {
  hideStatus();
  const caseData = getFormData();

  try {
    const [tab] = await chrome.tabs.query({
      active: true,
      currentWindow: true,
    });

    if (
      !tab.url ||
      !tab.url.includes("apps.acgme.org/ads/CaseLogs/CaseEntry")
    ) {
      showStatus("Navigate to ACGME Case Entry page first", "error");
      return;
    }

    const delayMs = Math.round(settings.submitDelay * 1000);

    const results = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: (data, submit, delay) => {
        if (typeof window.fillACGMECase === "function") {
          const result = window.fillACGMECase(data);
          if (
            submit &&
            result &&
            result.success &&
            typeof window.submitACGMECase === "function"
          ) {
            return new Promise((resolve) => {
              setTimeout(() => {
                window.submitACGMECase();
                resolve({ ...result, submitted: true });
              }, delay);
            });
          }
          return { ...result, submitted: false };
        }
        throw new Error("Content script not loaded. Refresh the ACGME page.");
      },
      args: [caseData, andSubmit, delayMs],
    });

    const result = results[0]?.result;
    if (result?.success) {
      // Show warnings if any
      if (result.warnings && result.warnings.length > 0) {
        console.warn("Fill warnings:", result.warnings);
      }

      if (andSubmit && result.submitted) {
        caseStatuses[currentIndex] = "submitted";
        let msg = "Form filled and submitted!";
        if (result.warnings && result.warnings.length > 0) {
          msg += ` Warning: ${result.warnings.join("; ")}`;
        }
        showStatus(msg, result.warnings?.length ? "info" : "success");
        updateNavigation();
        saveState();
        setTimeout(() => goToNextPending(), 1000);
      } else {
        let msg = "Form filled! Review and submit on the ACGME page.";
        if (result.warnings && result.warnings.length > 0) {
          msg = `Form filled with warnings: ${result.warnings.join("; ")}`;
        }
        showStatus(msg, "info");
      }
    } else if (result?.errors) {
      showStatus(`Error filling form: ${result.errors.join("; ")}`, "error");
    }
  } catch (error) {
    showStatus(error.message || "Error filling form", "error");
    console.error(error);
  }
}

// Event Listeners
document.getElementById("uploadBtn").addEventListener("click", () => {
  document.getElementById("fileInput").click();
});

document.getElementById("fileInput").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) {
    return;
  }

  document.getElementById("fileName").textContent = file.name;

  try {
    cases = await parseExcelFile(file);
    if (cases.length === 0) {
      showStatus("No valid cases found in file", "error");
      return;
    }

    caseStatuses = {};
    for (let i = 0; i < cases.length; i++) {
      caseStatuses[i] = "pending";
    }

    currentIndex = 0;
    showCases();
    populateForm(cases[0]);
    updateNavigation();
    saveState();
    showStatus(`Loaded ${cases.length} cases`, "success");
  } catch (error) {
    showStatus(`Error parsing file: ${error.message}`, "error");
    console.error(error);
  }
});

document.getElementById("prevBtn").addEventListener("click", () => {
  goToCase(currentIndex - 1);
});

document.getElementById("nextBtn").addEventListener("click", () => {
  goToCase(currentIndex + 1);
});

document.getElementById("caseJump").addEventListener("change", (e) => {
  goToCase(parseInt(e.target.value, 10));
});

document.getElementById("filterPending").addEventListener("change", () => {
  updateNavigation();
});

document.getElementById("skipBtn").addEventListener("click", () => {
  caseStatuses[currentIndex] = "skipped";
  updateNavigation();
  saveState();
  goToNextPending();
});

document.getElementById("fillBtn").addEventListener("click", () => {
  fillForm(false);
});

document.getElementById("fillSubmitBtn").addEventListener("click", () => {
  if (!pendingSubmission) {
    showConfirmation();
  }
});

document.getElementById("cancelSubmitBtn").addEventListener("click", () => {
  hideConfirmation();
});

document.getElementById("confirmSubmitBtn").addEventListener("click", () => {
  hideConfirmation();
  fillForm(true);
});

// Settings event listeners
document.getElementById("settingsToggle").addEventListener("click", () => {
  const settingsSection = document.getElementById("settingsSection");
  settingsSection.classList.toggle("hidden");
});

document.getElementById("settingSubmitDelay").addEventListener("input", (e) => {
  document.getElementById("submitDelayValue").textContent =
    `${e.target.value}s`;
});

document.getElementById("saveSettingsBtn").addEventListener("click", () => {
  saveSettings();
});

document.getElementById("clearSessionBtn").addEventListener("click", () => {
  if (confirm("Clear all loaded cases and progress? This cannot be undone.")) {
    clearSession();
  }
});

document.addEventListener("keydown", (e) => {
  if (cases.length === 0) {
    return;
  }

  if (e.key === "ArrowLeft" && !e.target.matches("input, textarea, select")) {
    e.preventDefault();
    goToCase(currentIndex - 1);
  } else if (
    e.key === "ArrowRight" &&
    !e.target.matches("input, textarea, select")
  ) {
    e.preventDefault();
    goToCase(currentIndex + 1);
  } else if (e.key === "Escape" && pendingSubmission) {
    hideConfirmation();
  }
});

// Initialize on load
document.addEventListener("DOMContentLoaded", async () => {
  await loadSettings();
  await loadState();
});
