# ACGME Case Auto-Fill Chrome Extension

Automatically fill ACGME case entry forms using data exported from the case-parser tool.

## Features

- 📤 Upload JSON files exported from case-parser
- 📋 View and select cases from your export
- ⚡ One-click form filling
- ✅ Auto-populate all standard fields
- 🔍 Review before submission (no auto-submit)

## Installation

### Option 1: Load Unpacked Extension (Development)

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable "Developer mode" (toggle in top right)
3. Click "Load unpacked"
4. Select the `chrome-extension` directory
5. The extension should now appear in your extensions list

### Option 2: Icons Setup

Before loading the extension, you'll need to add icon files:

1. Create an `icons` directory: `mkdir chrome-extension/icons`
2. Add three PNG icon files:
   - `icon16.png` (16x16 pixels)
   - `icon48.png` (48x48 pixels)
   - `icon128.png` (128x128 pixels)

You can use any icon design tool or create simple placeholder icons.

## Usage

### Step 1: Export Cases from Excel

Use the case-parser CLI to export your cases to JSON:

```bash
case-parser input.xlsx output.xlsx --json-export cases.json --resident-id "YOUR_ID"
```

With program information:

```bash
case-parser input.xlsx output.xlsx \
  --json-export cases.json \
  --resident-id "1325527" \
  --program-id "0404121134" \
  --program-name "University of Pennsylvania Health System Program"
```

### Step 2: Navigate to ACGME

1. Log into https://apps.acgme.org
2. Navigate to Case Logs → Add Cases
3. The URL should be: `https://apps.acgme.org/ads/CaseLogs/CaseEntry/Insert`

### Step 3: Use the Extension

1. Click the extension icon in Chrome toolbar
2. Click "Choose JSON File" and select your exported `cases.json`
3. Select a case from the list
4. Click "Fill Form with This Case"
5. **Review the auto-filled data carefully**
6. Click the ACGME "Submit" button manually

## What Gets Auto-Filled

The extension automatically fills:

- **Case ID** - Unique case identifier
- **Case Date** - Date of procedure
- **Case Year** - Residency year
- **Site/Institution** - Hospital/facility
- **Supervisor** - Attending physician
- **Patient Age Category** - Age group (a-e)
- **Procedure Codes** - ASA status, anesthesia types, airway management, etc.
- **Comments** - Any notes (if present)

## Important Notes

⚠️ **Always Review Before Submitting**
- The extension does NOT auto-submit forms
- You must review all filled data for accuracy
- Manually click Submit after verification

⚠️ **Session Requirements**
- You must be logged into ACGME
- The extension works with your existing session
- No credentials are stored

⚠️ **Supported Pages**
- Only works on: `https://apps.acgme.org/ads/CaseLogs/CaseEntry/*`
- Will show a warning if you're on the wrong page

## Troubleshooting

### "Error: chrome.runtime.lastError"
- Refresh the ACGME page
- Reload the extension in `chrome://extensions/`
- Try logging out and back into ACGME

### "Procedure code not found" warnings
- Some procedure codes may have changed on ACGME's end
- Check the browser console (F12) for specific codes
- You may need to manually select missing procedures

### Form fields not filling
- Ensure you're on the correct ACGME page
- Check that the JSON file is in the correct format
- Look for errors in the browser console (F12)

## JSON Format

Expected JSON structure (from case-parser):

```json
{
  "metadata": {
    "export_date": "2025-01-15T12:00:00",
    "total_cases": 1,
    "tool_version": "1.0.0",
    "format_version": "1.0"
  },
  "cases": [
    {
      "row_number": 1,
      "case_id": "CASE001",
      "case_date": "11/15/2025",
      "case_year": 2,
      "resident_id": "1325527",
      "institution": {
        "name": "University of Pennsylvania Health System",
        "code": "12748"
      },
      "supervisor": {
        "name": "FACULTY, FACULTY",
        "code": "255593"
      },
      "patient": {
        "age_category": "d. >= 12 yr. and < 65 yr.",
        "age_code": "33"
      },
      "asa_status": {
        "text": "ASA 2",
        "code": "156632"
      },
      "procedure_codes": [
        "156632",
        "1256330",
        "156654"
      ],
      "comments": ""
    }
  ]
}
```

## Privacy & Security

- No data is sent to external servers
- All processing happens locally in your browser
- Data is stored in Chrome's local storage only
- No analytics or tracking
- No credentials are collected or stored

## Development

### File Structure
```
chrome-extension/
├── manifest.json       # Extension configuration
├── popup.html          # Extension popup UI
├── popup.css           # Popup styling
├── popup.js            # Popup logic
├── content.js          # Form filling logic
├── content.css         # Content script styles
├── icons/              # Extension icons
│   ├── icon16.png
│   ├── icon48.png
│   └── icon128.png
└── README.md          # This file
```

### Testing
1. Make changes to the code
2. Go to `chrome://extensions/`
3. Click the refresh icon on the extension card
4. Test on ACGME case entry page

### Debugging
- Open popup: Right-click extension icon → "Inspect popup"
- Check content script: Open DevTools (F12) on ACGME page
- Console logs are prefixed with `[ACGME Auto-Fill]`

## Contributing

Improvements welcome! Areas for enhancement:
- Better error handling
- Support for more case types
- Batch submission (queue multiple cases)
- Template support
- Export submission logs

## License

MIT License - See main project LICENSE file

## Disclaimer

This extension is not affiliated with or endorsed by ACGME. Use at your own risk. Always verify the accuracy of auto-filled data before submission.

## Support

For issues or questions:
1. Check the Troubleshooting section above
2. Review browser console errors (F12)
3. Open an issue in the project repository

## Version History

### v1.0.0 (2025-01-15)
- Initial release
- Basic form filling functionality
- Support for standard ACGME case entry fields
- JSON import from case-parser exports
