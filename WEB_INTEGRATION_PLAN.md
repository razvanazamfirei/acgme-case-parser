# Web Form Integration Plan for ACGME Case Submission

## Overview
This document outlines the strategy for integrating the case-parser tool with the ACGME web form to automate case log submissions.

## Current State Analysis

### ACGME API Endpoint
- **URL**: `https://apps.acgme.org/ads/CaseLogs/CaseEntry/Insert`
- **Method**: POST
- **Content-Type**: `application/x-www-form-urlencoded`

### Authentication Requirements
1. **Session Cookies** (required):
   - `ACGMEADSAuthToken` - Main authentication token (encrypted, long-lived)
   - `BNES_ACGMEADSAuthToken` - Backup/secondary auth token
   - `ASP.NET_SessionId` - ASP.NET session identifier
   - `BNES_ASP.NET_SessionId` - Backup session ID

2. **CSRF Protection**:
   - `__RequestVerificationToken` cookie
   - `__RequestVerificationToken` form field (must match cookie)
   - These tokens are page-specific and must be extracted from the form page

### Form Data Structure
Based on the example, the form includes:

**Required Fields**:
- `__RequestVerificationToken` - CSRF token
- `Residents` - Resident ID (e.g., "1325527")
- `ProcedureYear` - Case year (e.g., "2")
- `Institutions` - Site/hospital ID (e.g., "12748")
- `Attendings` - Supervisor ID (e.g., "255593")
- `PatientTypes` - Patient age category (e.g., "33")
- Case Date (hashed field name: `5b1ce523d862b284baf78d6c3d9a600a957dbf929d880ddc9256ac5e8dd02b54`)
- Case ID (hashed field name: `71291aeec5a9d7383731151a615f5f0d3418ffdea0630e0b8dfab7161a5854b8`)

**Procedure Selection**:
- `SelectedCodes` - Comma-separated procedure IDs (e.g., "156632,156633,1256332,...")
- `SelectedCodeAttributes` - Procedure attributes
- `procedures` - Procedure group ID (e.g., "681")

**Optional Fields**:
- `Comments` - Case comments
- `CaseTypes[0]`, `CaseTypes[1]` - Life-threatening pathology, difficult airway flags
- Template fields for saving case templates

## Integration Approaches

### Option 1: Chrome Extension (Recommended)
**Pros**:
- Access to existing authentication session
- No need to handle login/MFA
- Can inject data directly into the web form
- User stays in control of submission
- Can validate data before submission

**Cons**:
- Requires Chrome/browser installation
- Platform-dependent
- Requires manifest v3 knowledge

**Implementation Steps**:
1. Create Chrome extension with content script
2. Parse Excel output from case-parser
3. Inject parsed data into form fields
4. Optionally auto-submit or let user review
5. Handle CSRF tokens automatically from page

**Technical Architecture**:
```
┌─────────────────┐
│  Excel File     │
│  (Input)        │
└────────┬────────┘
         │
         v
┌─────────────────┐
│  case-parser    │
│  CLI Tool       │
└────────┬────────┘
         │
         v
┌─────────────────┐
│  JSON/CSV       │
│  (Intermediate) │
└────────┬────────┘
         │
         v
┌─────────────────┐
│  Chrome Ext     │
│  Content Script │
└────────┬────────┘
         │
         v
┌─────────────────┐
│  ACGME Web Form │
│  (Auto-filled)  │
└─────────────────┘
```

### Option 2: Standalone API Client
**Pros**:
- Platform-independent
- Can be fully automated
- Scriptable for bulk operations

**Cons**:
- Must handle authentication flow (complex)
- Must handle MFA (likely impossible to automate)
- Must scrape/parse HTML for form tokens
- Risk of account lockout
- Violates likely ToS

**Not Recommended** due to authentication complexity and MFA requirements.

### Option 3: Hybrid Approach (Browser Automation)
Use Selenium/Playwright to:
1. Leverage existing browser session
2. Automate form filling
3. Handle complex interactions

**Pros**:
- Can reuse authentication
- More control than extension
- Can handle complex workflows

**Cons**:
- Requires browser driver
- Slower than direct API
- More fragile (DOM changes break it)
- User must stay logged in

## Recommended Solution: Chrome Extension

### Architecture Design

#### 1. Extension Components

**manifest.json** (Manifest V3):
```json
{
  "manifest_version": 3,
  "name": "ACGME Case Auto-Fill",
  "version": "1.0.0",
  "permissions": ["storage", "activeTab"],
  "host_permissions": ["https://apps.acgme.org/*"],
  "content_scripts": [{
    "matches": ["https://apps.acgme.org/ads/CaseLogs/CaseEntry/Insert"],
    "js": ["content.js"]
  }],
  "action": {
    "default_popup": "popup.html"
  }
}
```

**popup.html** - User interface:
- File upload for JSON/CSV from case-parser
- Display parsed cases
- Buttons to fill form for each case
- Progress indicator

**content.js** - Form interaction:
- Detect ACGME case entry form
- Map parsed data to form fields
- Fill form fields programmatically
- Handle procedure code selection
- Validate data before submission

#### 2. Data Flow

```
case-parser output (JSON) → Chrome Extension → ACGME Form
```

**JSON Schema for case-parser output**:
```json
{
  "cases": [
    {
      "case_id": "test",
      "case_date": "11/15/2025",
      "case_year": 2,
      "site": "University of Pennsylvania Health System",
      "site_id": "12748",
      "supervisor": "FACULTY, FACULTY",
      "supervisor_id": "255593",
      "patient_age": "d. >= 12 yr. and < 65 yr.",
      "patient_age_id": "33",
      "procedures": [
        {
          "code": "156632",
          "name": "ASA 2",
          "category": "ASA Physical Status"
        }
      ],
      "comments": "",
      "case_types": []
    }
  ]
}
```

#### 3. Field Mapping Strategy

The extension needs to map our standardized data to ACGME form fields:

**Mapping Table**:
| Our Field | ACGME Field | Type | Notes |
|-----------|-------------|------|-------|
| case_id | 71291aee... (hashed) | text | Field name is hashed |
| case_date | 5b1ce523... (hashed) | date | Field name is hashed |
| case_year | ProcedureYear | select | Direct mapping |
| site_id | Institutions | select | Must match their IDs |
| supervisor_id | Attendings | select | Must match their IDs |
| patient_age_id | PatientTypes | select | Must match their IDs |
| procedures | SelectedCodes | hidden | Comma-separated IDs |
| comments | Comments | textarea | Optional |

**Challenges**:
1. **Hashed field names**: Field names appear to be hashed/obfuscated
   - Solution: Use DOM selectors based on labels or data attributes

2. **Dynamic IDs**: Procedure codes, sites, and supervisors have numeric IDs
   - Solution: Build lookup tables or fuzzy matching

3. **Procedure selection UI**: Complex checkbox system
   - Solution: Programmatically check boxes based on codes

4. **Template system**: Forms support templates
   - Solution: Either use templates or fill manually each time

### Implementation Phases

#### Phase 1: Data Export Enhancement
**Goal**: Modify case-parser to output web-friendly format

**Tasks**:
1. Add JSON export format to case-parser
2. Include procedure codes in output
3. Map to ACGME field structure
4. Create lookup tables for sites/supervisors

**Files to create**:
- `src/case_parser/web_exporter.py` - JSON export logic
- `src/case_parser/acgme_mappings.py` - Field mappings

#### Phase 2: Chrome Extension MVP
**Goal**: Basic form filling functionality

**Tasks**:
1. Create extension scaffold (manifest, popup, content script)
2. Implement JSON file upload in popup
3. Detect ACGME form fields in content script
4. Fill basic fields (date, site, supervisor, patient age)
5. Test with manual submission

**Files to create**:
- `chrome-extension/manifest.json`
- `chrome-extension/popup.html`
- `chrome-extension/popup.js`
- `chrome-extension/content.js`
- `chrome-extension/styles.css`

#### Phase 3: Procedure Code Handling
**Goal**: Automate procedure selection

**Tasks**:
1. Parse procedure checkboxes on ACGME form
2. Build procedure code to checkbox mapping
3. Implement checkbox selection logic
4. Handle multiple procedures per case
5. Validate procedure combinations

#### Phase 4: Batch Processing
**Goal**: Submit multiple cases efficiently

**Tasks**:
1. Add case queue to extension
2. Implement case-by-case filling
3. Add progress tracking
4. Handle submission confirmations
5. Error handling and retry logic

#### Phase 5: Advanced Features
**Goal**: Enhanced user experience

**Tasks**:
1. Template support for common case types
2. Draft mode (fill without submit)
3. Validation warnings before submission
4. Export submission log
5. Dark mode for extension UI

### Technical Considerations

#### 1. Field Name Obfuscation
The ACGME form uses hashed field names (e.g., `71291aeec5a9d7383731151a615f5f0d3418ffdea0630e0b8dfab7161a5854b8`).

**Solutions**:
- Use label text to find fields: `document.querySelector('label:contains("Case ID")').nextElementSibling`
- Use data attributes if available
- Use DOM structure (nth-child selectors)
- Maintain a mapping of known hashed names

#### 2. CSRF Token Extraction
**Method**:
```javascript
// Extract from hidden field
const token = document.querySelector('input[name="__RequestVerificationToken"]').value;

// Or from cookie
const tokenCookie = document.cookie.split('; ')
  .find(row => row.startsWith('__RequestVerificationToken_L2Fkcw2='))
  ?.split('=')[1];
```

#### 3. Procedure Code Selection
The form has complex procedure selection with:
- Multiple collapsible panels
- Checkboxes organized by category
- Mutual exclusivity rules
- Quantity inputs for some procedures

**Strategy**:
```javascript
// Find checkbox by procedure ID
function selectProcedure(procedureId) {
  const checkbox = document.getElementById(procedureId);
  if (checkbox && !checkbox.checked) {
    checkbox.click(); // Trigger click to fire any event handlers
  }
}

// Select multiple procedures
function selectProcedures(procedureIds) {
  procedureIds.forEach(id => selectProcedure(id));
}
```

#### 4. Form Submission
Two options:
1. **Auto-submit**: `document.querySelector('form').submit()`
2. **Click button**: `document.querySelector('#submitButton').click()`

Recommendation: Click the button to ensure client-side validation runs.

#### 5. Error Handling
Monitor for:
- Validation errors (server-side)
- Session timeouts
- Network errors
- Duplicate case warnings

**Implementation**:
```javascript
// Watch for error messages
const observer = new MutationObserver((mutations) => {
  mutations.forEach((mutation) => {
    mutation.addedNodes.forEach((node) => {
      if (node.classList?.contains('alert-danger')) {
        // Handle error
        console.error('Submission error:', node.textContent);
      }
    });
  });
});
observer.observe(document.body, { childList: true, subtree: true });
```

## Security and Compliance

### Concerns
1. **Terms of Service**: Automated submission may violate ACGME ToS
2. **Data Privacy**: Handle PHI carefully (case IDs should be de-identified)
3. **Authentication**: Don't store or transmit credentials
4. **Rate Limiting**: Respect server resources, add delays between submissions

### Recommendations
1. **User Consent**: Clear disclaimer about automated submission
2. **Review Before Submit**: Allow user to review each case
3. **No Credential Storage**: Rely on browser's existing session
4. **Audit Trail**: Log what was submitted
5. **Data Encryption**: Encrypt any stored intermediate data

## Alternative: Bookmarklet (Quick Prototype)
For rapid prototyping, consider a bookmarklet that:
1. Prompts for JSON input
2. Fills current form
3. Requires manual submission

**Example**:
```javascript
javascript:(function(){
  const json = prompt('Paste case JSON:');
  const data = JSON.parse(json);
  // Fill form fields
  document.querySelector('#71291aeec5a9d7383731151a615f5f0d3418ffdea0630e0b8dfab7161a5854b8').value = data.case_id;
  // ... more fields
})();
```

## Next Steps

### Immediate Actions
1. ✅ Commit current changes (completed)
2. 📝 Create `web_exporter.py` to output JSON format
3. 🔍 Analyze ACGME form HTML structure in detail
4. 🏗️ Build Chrome extension scaffold
5. 🧪 Test with a single case submission

### Future Enhancements
- Optical Character Recognition (OCR) for paper logs
- Mobile app for on-the-go case entry
- Integration with EHR systems
- Analytics dashboard for case statistics
- Multi-resident support for program coordinators

## Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Form structure changes | High | Medium | Version detection, graceful degradation |
| Session timeout | Medium | High | Detect and prompt user to re-auth |
| Validation errors | Medium | Medium | Pre-validate data, show clear errors |
| Account suspension | High | Low | User review, rate limiting, ToS compliance |
| Data loss | High | Low | Local backup, confirmation dialogs |

## Conclusion

**Recommended Approach**: Chrome Extension
- **Timeline**: 2-3 weeks for MVP
- **Effort**: Medium (requires HTML parsing, Chrome API knowledge)
- **User Experience**: Excellent (seamless integration)
- **Maintainability**: Good (isolated from auth complexity)

**Success Criteria**:
- Fill form fields with 95%+ accuracy
- Handle 100 cases/session without errors
- Complete case entry in < 30 seconds per case
- Zero data loss or corruption
- Graceful error handling and recovery
