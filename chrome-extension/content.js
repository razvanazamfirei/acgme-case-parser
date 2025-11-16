// content.js - Content script that fills ACGME case entry form

console.log('[ACGME Auto-Fill] Content script loaded');

// Listen for messages from popup
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'fillForm') {
        try {
            fillACGMEForm(request.caseData);
            sendResponse({ success: true });
        } catch (error) {
            console.error('[ACGME Auto-Fill] Error filling form:', error);
            sendResponse({ success: false, error: error.message });
        }
        return true; // Keep the message channel open for async response
    }
});

/**
 * Main function to fill the ACGME case entry form
 */
function fillACGMEForm(caseData) {
    console.log('[ACGME Auto-Fill] Filling form with case data:', caseData);

    // Fill basic fields
    fillCaseID(caseData.case_id);
    fillCaseDate(caseData.case_date);
    fillCaseYear(caseData.case_year);

    // Fill dropdowns
    fillInstitution(caseData.institution);
    fillSupervisor(caseData.supervisor);
    fillPatientAge(caseData.patient);

    // Fill procedure codes (checkboxes)
    fillProcedureCodes(caseData.procedure_codes || []);

    // Fill comments if any
    if (caseData.comments) {
        fillComments(caseData.comments);
    }

    console.log('[ACGME Auto-Fill] Form filling complete');
}

/**
 * Fill Case ID field
 */
function fillCaseID(caseID) {
    if (!caseID) return;

    // The Case ID field has a hashed name, so we find it by its label
    const labels = Array.from(document.querySelectorAll('label'));
    const caseIDLabel = labels.find(label => label.textContent.trim() === 'Case ID');

    if (caseIDLabel) {
        // Find the input next to the label
        const input = caseIDLabel.parentElement?.querySelector('input[type="text"]');
        if (input) {
            input.value = caseID;
            input.dispatchEvent(new Event('change', { bubbles: true }));
            console.log('[ACGME Auto-Fill] Set Case ID:', caseID);
        }
    }
}

/**
 * Fill Case Date field
 */
function fillCaseDate(date) {
    if (!date) return;

    const labels = Array.from(document.querySelectorAll('label'));
    const dateLabel = labels.find(label => label.textContent.includes('Case Date'));

    if (dateLabel) {
        const input = dateLabel.parentElement?.querySelector('input[type="text"]');
        if (input) {
            input.value = date;
            input.dispatchEvent(new Event('change', { bubbles: true }));
            console.log('[ACGME Auto-Fill] Set Case Date:', date);
        }
    }
}

/**
 * Fill Case Year dropdown
 */
function fillCaseYear(year) {
    if (!year) return;

    const select = document.querySelector('select#ProcedureYear, select[name="ProcedureYear"]');
    if (select) {
        select.value = String(year);
        select.dispatchEvent(new Event('change', { bubbles: true }));
        console.log('[ACGME Auto-Fill] Set Case Year:', year);
    }
}

/**
 * Fill Institution/Site dropdown
 */
function fillInstitution(institution) {
    if (!institution || !institution.code) return;

    const select = document.querySelector('select#Institutions, select[name="Institutions"]');
    if (select) {
        select.value = institution.code;
        select.dispatchEvent(new Event('change', { bubbles: true }));
        console.log('[ACGME Auto-Fill] Set Institution:', institution.name);
    }
}

/**
 * Fill Supervisor dropdown
 */
function fillSupervisor(supervisor) {
    if (!supervisor || !supervisor.code) return;

    const select = document.querySelector('select#Attendings, select[name="Attendings"]');
    if (select) {
        select.value = supervisor.code;
        select.dispatchEvent(new Event('change', { bubbles: true }));
        console.log('[ACGME Auto-Fill] Set Supervisor:', supervisor.name);
    }
}

/**
 * Fill Patient Age dropdown
 */
function fillPatientAge(patient) {
    if (!patient || !patient.age_code) return;

    const select = document.querySelector('select#PatientTypes, select[name="PatientTypes"]');
    if (select) {
        select.value = patient.age_code;
        select.dispatchEvent(new Event('change', { bubbles: true }));
        console.log('[ACGME Auto-Fill] Set Patient Age:', patient.age_category);
    }
}

/**
 * Fill procedure code checkboxes
 */
function fillProcedureCodes(procedureCodes) {
    if (!procedureCodes || procedureCodes.length === 0) return;

    console.log('[ACGME Auto-Fill] Filling procedure codes:', procedureCodes);

    let filledCount = 0;

    procedureCodes.forEach(code => {
        // Find checkbox by ID (procedure codes are checkbox IDs)
        const checkbox = document.getElementById(code);
        if (checkbox && checkbox.type === 'checkbox') {
            if (!checkbox.checked) {
                checkbox.click(); // Use click to trigger any event handlers
                filledCount++;
                console.log('[ACGME Auto-Fill] Checked procedure code:', code);
            }
        } else {
            console.warn('[ACGME Auto-Fill] Procedure code not found:', code);
        }
    });

    console.log(`[ACGME Auto-Fill] Filled ${filledCount}/${procedureCodes.length} procedure codes`);
}

/**
 * Fill comments field
 */
function fillComments(comments) {
    if (!comments) return;

    const textarea = document.querySelector('textarea#Comments, textarea[name="Comments"]');
    if (textarea) {
        textarea.value = comments;
        textarea.dispatchEvent(new Event('change', { bubbles: true }));
        console.log('[ACGME Auto-Fill] Set Comments');
    }
}

/**
 * Helper function to find select option by text (case-insensitive)
 */
function selectOptionByText(selectElement, text) {
    if (!selectElement || !text) return false;

    const options = Array.from(selectElement.options);
    const matchingOption = options.find(option =>
        option.text.toLowerCase().includes(text.toLowerCase()) ||
        text.toLowerCase().includes(option.text.toLowerCase())
    );

    if (matchingOption) {
        selectElement.value = matchingOption.value;
        selectElement.dispatchEvent(new Event('change', { bubbles: true }));
        return true;
    }

    return false;
}

/**
 * Helper function to wait for element to appear
 */
function waitForElement(selector, timeout = 5000) {
    return new Promise((resolve, reject) => {
        const element = document.querySelector(selector);
        if (element) {
            resolve(element);
            return;
        }

        const observer = new MutationObserver((mutations, obs) => {
            const element = document.querySelector(selector);
            if (element) {
                obs.disconnect();
                resolve(element);
            }
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });

        setTimeout(() => {
            observer.disconnect();
            reject(new Error(`Element ${selector} not found within ${timeout}ms`));
        }, timeout);
    });
}

// Show visual feedback when form is filled
function showFeedback() {
    const banner = document.createElement('div');
    banner.id = 'acgme-autofill-banner';
    banner.textContent = '✓ Form auto-filled successfully! Please review before submitting.';
    banner.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: #48bb78;
        color: white;
        padding: 12px 20px;
        border-radius: 6px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 10000;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        font-size: 14px;
        font-weight: 500;
        animation: slideIn 0.3s ease-out;
    `;

    // Add CSS animation
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideIn {
            from {
                transform: translateX(400px);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
    `;
    document.head.appendChild(style);

    document.body.appendChild(banner);

    // Remove after 5 seconds
    setTimeout(() => {
        banner.style.transition = 'opacity 0.3s';
        banner.style.opacity = '0';
        setTimeout(() => banner.remove(), 300);
    }, 5000);
}
