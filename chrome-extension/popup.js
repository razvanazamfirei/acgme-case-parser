// popup.js - Popup UI logic for case selection and form filling

let casesData = null;

// DOM elements
const uploadBtn = document.getElementById('uploadBtn');
const fileInput = document.getElementById('fileInput');
const fileName = document.getElementById('fileName');
const casesSection = document.getElementById('cases-section');
const casesList = document.getElementById('casesList');
const statusSection = document.getElementById('status-section');
const statusMessage = document.getElementById('statusMessage');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Load previously uploaded data if exists
    chrome.storage.local.get(['casesData'], (result) => {
        if (result.casesData) {
            casesData = result.casesData;
            displayCases(casesData.cases);
        }
    });

    // Set up event listeners
    uploadBtn.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', handleFileUpload);
});

/**
 * Handle JSON file upload
 */
function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    if (!file.name.endsWith('.json')) {
        showStatus('error', 'Please select a JSON file');
        return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
        try {
            const data = JSON.parse(e.target.result);

            // Validate data structure
            if (!data.cases || !Array.isArray(data.cases)) {
                showStatus('error', 'Invalid JSON format. Missing "cases" array');
                return;
            }

            casesData = data;
            fileName.textContent = file.name;

            // Store in chrome storage
            chrome.storage.local.set({ casesData: data }, () => {
                displayCases(data.cases);
                showStatus('success', `Loaded ${data.cases.length} cases from ${file.name}`);
            });

        } catch (error) {
            showStatus('error', `Failed to parse JSON: ${error.message}`);
        }
    };

    reader.readAsText(file);
}

/**
 * Display cases in the list
 */
function displayCases(cases) {
    if (!cases || cases.length === 0) {
        casesList.innerHTML = '<p style="text-align: center; color: #718096;">No cases found</p>';
        return;
    }

    casesSection.classList.remove('hidden');

    casesList.innerHTML = cases.map((caseData, index) => `
        <div class="case-item" data-index="${index}">
            <div class="case-item-header">
                <span class="case-id">${caseData.case_id || `Case ${index + 1}`}</span>
                <span class="case-date">${caseData.case_date || 'No date'}</span>
            </div>
            <div class="case-details">
                <div><strong>Year:</strong> ${caseData.case_year || 'N/A'}</div>
                <div><strong>Site:</strong> ${caseData.institution?.name || 'N/A'}</div>
                <div><strong>Age:</strong> ${caseData.patient?.age_category || 'N/A'}</div>
                <div><strong>ASA:</strong> ${caseData.asa_status?.text || 'N/A'}</div>
                <div><strong>Procedures:</strong> ${caseData.procedure_codes?.length || 0} codes</div>
            </div>
            <button class="btn btn-secondary fill-btn" data-index="${index}">
                Fill Form with This Case
            </button>
        </div>
    `).join('');

    // Add click handlers to fill buttons
    document.querySelectorAll('.fill-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const index = parseInt(e.target.dataset.index);
            fillFormWithCase(cases[index]);
        });
    });
}

/**
 * Fill form with selected case data
 */
async function fillFormWithCase(caseData) {
    try {
        // Get active tab
        const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

        // Check if we're on the ACGME case entry page
        if (!tab.url || !tab.url.includes('apps.acgme.org/ads/CaseLogs/CaseEntry')) {
            showStatus('warning', 'Please navigate to the ACGME Case Entry page first');
            return;
        }

        // Send message to content script
        chrome.tabs.sendMessage(tab.id, {
            action: 'fillForm',
            caseData: caseData
        }, (response) => {
            if (chrome.runtime.lastError) {
                showStatus('error', `Error: ${chrome.runtime.lastError.message}`);
                return;
            }

            if (response && response.success) {
                showStatus('success', 'Form filled successfully! Please review and submit manually.');
            } else {
                showStatus('error', response?.error || 'Failed to fill form');
            }
        });

    } catch (error) {
        showStatus('error', `Error: ${error.message}`);
    }
}

/**
 * Show status message
 */
function showStatus(type, message) {
    statusSection.classList.remove('hidden');
    statusMessage.className = `status-message ${type}`;
    statusMessage.textContent = message;

    // Auto-hide success messages after 5 seconds
    if (type === 'success') {
        setTimeout(() => {
            statusSection.classList.add('hidden');
        }, 5000);
    }
}
