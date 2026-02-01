"""
Anesthesia Type Mapping Rules.

This file contains mappings to convert various anesthesia type descriptions
from source data into standardized anesthesia type categories.

FIELDS EXTRACTED:
- Anesthesia Type (GA, MAC, Spinal, Epidural, CSE, Peripheral nerve block)

MODIFICATION GUIDE:
The mapping uses keyword matching. If a keyword is found in the input text,
it maps to the corresponding standardized type.

To add a new mapping:
1. Add the keyword (in uppercase) as a key
2. Map it to one of the standardized types:
   - "GA" (General Anesthesia)
   - "MAC" (Monitored Anesthesia Care)
   - "Spinal"
   - "Epidural"
   - "CSE" (Combined Spinal-Epidural)
   - "Peripheral nerve block"

MATCHING BEHAVIOR:
- Keywords are matched against UPPERCASE input text
- First matching keyword wins
- If no match found, original input is returned unchanged
"""

# ============================================================================
# ANESTHESIA TYPE MAPPINGS
# ============================================================================
# Maps keywords found in anesthesia type field to standardized categories
ANESTHESIA_MAPPING = {
    # Combined Spinal-Epidural
    "CSE": "CSE",
    # Epidural anesthesia
    "EPIDURAL": "Epidural",
    # Spinal anesthesia
    "SPINAL": "Spinal",
    # Peripheral nerve blocks
    "BLOCK": "Peripheral nerve block",
    "PNB": "Peripheral nerve block",  # Peripheral Nerve Block abbreviation
    # Monitored Anesthesia Care / Sedation
    "MAC": "MAC",
    "SEDATION": "MAC",
    # General Anesthesia
    "GENERAL": "GA",
    "ENDOTRACHEAL": "GA",  # Endotracheal intubation implies GA
}
