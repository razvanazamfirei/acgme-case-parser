# Pattern Extraction Modules

This directory contains all pattern-based extraction logic for the case parser. Each module is self-contained with patterns, extraction logic, and documentation.

## Directory Organization

```
patterns/
├── README.md                    # This file
├── __init__.py                  # Exports all patterns and extraction functions
├── extraction_utils.py          # Shared utilities for pattern matching
│
├── airway_patterns.py           # Airway management extraction
├── vascular_access_patterns.py  # Vascular access extraction
├── monitoring_patterns.py       # Specialized monitoring extraction
│
├── procedure_patterns.py        # Procedure categorization rules
├── categorization.py            # Procedure categorization logic
├── approach_patterns.py         # Surgical approach detection
│
├── age_patterns.py              # Age range categorization
└── anesthesia_patterns.py       # Anesthesia type mapping
```

## Module Guide

### Extraction Modules

These modules contain regex patterns and extraction functions:

#### `airway_patterns.py`

**What it extracts:**

- Intubation type (oral vs nasal ETT)
- Laryngoscopy technique (direct vs video)
- Alternative airways (LMA, mask ventilation)
- Bronchoscopy
- Difficult airway encounters

**Key patterns:**

- `INTUBATION_PATTERNS` - Detects any intubation
- `DIRECT_LARYNGOSCOPY_PATTERNS` - Miller blade, Macintosh blade
- `VIDEO_LARYNGOSCOPY_PATTERNS` - Glidescope, C-MAC, McGrath
- `SUPRAGLOTTIC_PATTERNS` - LMA, i-gel, Air-Q
- `NEGATION_PATTERNS` - Phrases like "no intubation" (reduces confidence)

**Example:**

```python
from case_parser.patterns import extract_airway_management

notes = "Patient intubated with video laryngoscopy using Glidescope"
techniques, findings = extract_airway_management(notes)
# techniques: [AirwayManagement.ORAL_ETT, AirwayManagement.VIDEO_LARYNGOSCOPE]
```

#### `vascular_patterns.py`

**What it extracts:**

- Arterial lines (A-line, radial, femoral)
- Central venous catheters (IJ, subclavian, femoral)
- Pulmonary artery catheters (Swan-Ganz)

**Key patterns:**

- `ARTERIAL_LINE_PATTERNS` - A-line, arterial catheter
- `CENTRAL_LINE_PATTERNS` - CVC, IJ, subclavian
- `PA_CATHETER_PATTERNS` - Swan-Ganz, PAC

**Example:**

```python
from case_parser.patterns import extract_vascular_access

notes = "Right radial A-line and CVC via right IJ"
access, findings = extract_vascular_access(notes)
# access: [VascularAccess.ARTERIAL_CATHETER, VascularAccess.CENTRAL_VENOUS_CATHETER]
```

#### `monitoring_patterns.py`

**What it extracts:**

- TEE (transesophageal echocardiography)
- Electrophysiologic monitoring (SSEP, MEP, EMG)
- CSF drains (lumbar drains)
- Invasive neurological monitoring (ICP, ventriculostomy)

**Key patterns:**

- `TEE_PATTERNS` - TEE, transesophageal echo
- `ELECTROPHYSIOLOGIC_PATTERNS` - SSEP, neuromonitoring
- `CSF_DRAIN_PATTERNS` - Lumbar drain, CSF catheter
- `INVASIVE_NEURO_PATTERNS` - ICP monitor, EVD

**Example:**

```python
from case_parser.patterns import extract_monitoring

notes = "TEE performed, neuromonitoring with SSEPs"
monitoring, findings = extract_monitoring(notes)
# monitoring: [MonitoringTechnique.TEE, MonitoringTechnique.ELECTROPHYSIOLOGIC_MON]
```

### Categorization Modules

These modules handle procedure categorization:

#### `procedure_patterns.py`

Contains the rule definitions for matching services to procedure categories.

**Structure:**

```python
ProcedureRule(
    keywords=["CARDSURG", "CARDIAC"],      # Match these in service field
    exclude_keywords=["THORACIC"],          # Exclude if these are present
    category="Cardiac"                      # Assign this category
)
```

#### `categorization.py`

Contains the categorization logic for each surgery type:

**Functions:**

- `categorize_cardiac()` - Detects CPB vs non-CPB
- `categorize_vascular()` - Detects endovascular vs open
- `categorize_intracerebral()` - Detects approach and pathology
- `categorize_obgyn()` - Detects delivery type
- `categorize_procedure()` - Main entry point

**Example:**

```python
from case_parser.patterns import categorize_procedure

category, warnings = categorize_procedure("TAVR", ["CARDSURG"])
# category: ProcedureCategory.CARDIAC_WITHOUT_CPB
```

#### `approach_patterns.py`

Detects surgical approach (endovascular vs. open) and pathology type.

**Functions:**

- `detect_approach()` - Returns `endovascular`, `open`, or `None`
- `detect_intracerebral_pathology()` - Returns `vascular`, `nonvascular`, or `None`

### Configuration Modules

#### `age_patterns.py`

Defines age ranges for categorization (a-e labels).

#### `anesthesia_patterns.py`

Maps anesthesia type strings to standardized types.

## How to Debug Patterns

### Step 1: Run the Debug Script

```bash
# Test a specific procedure
python debug_categorization.py "TAVR" "CARDSURG"

# Interactive mode
python debug_categorization.py --interactive
```

### Step 2: Check Pattern Files

If a pattern isn't matching:

1. Open the relevant pattern file (e.g., `airway_patterns.py`).
2. Look at the pattern lists for the technique you're trying to match.
3. Check if your text contains the keywords.

### Step 3: Test Patterns Directly

```python
import re

# Test if your pattern matches
pattern = r"\bTAVR\b"
text = "Patient underwent TAVR procedure"
match = re.search(pattern, text, re.IGNORECASE)
print(f"Match: {match.group() if match else 'No match'}")
```

### Step 4: Add New Patterns

To add a new pattern, simply append it to the relevant list:

```python
# In airway_patterns.py
INTUBATION_PATTERNS = [
    r"\bintubat(ed|ion|e)?\b",
    r"\bETT\b",
    r"\bendotrache(al)?\b",
    r"\bnew_pattern_here\b",  # Add your pattern
]
```

## Pattern Writing Guide

### Regex Tips

**Word boundaries:**

```python
r"""\bETT\b"""  # Matches "ETT" but not "BETT" or "ETTA"
```

**Optional parts:**

```python
r"""\bintubat(ed|ion|e)?\b"""  # Matches: intubat, intubated, intubation, intubate
```

**Whitespace:**

```python
r"""\bvideo\s+laryngosc"""  # Matches "video laryngoscopy", "video  laryngoscopy"
```

**Case-insensitive:**
All patterns are automatically case-insensitive (re.IGNORECASE flag is used).

### Common Pitfalls

**Too specific:**

```python
# Bad: Won't match "radial arterial line"
r"""\bradial\s+artery\s+line\b"""

# Good: Matches variations
r"\bradial\s+(artery|arterial|line)\b"
```

**Too general:**

```python
# Bad: Matches "mask" in "face mask" when you want only LMA
r"""\bmask\b"""

# Good: Excludes LMA
r"\bmask\b(?!.*\bLMA\b)"
```

**Missing abbreviations:**

```python
# Bad: Only matches full term
r"""\btransesophageal\s+echocardiography\b"""

# Good: Matches both full and abbreviated
r"\b(TEE|transesophageal\s+echo(cardiograph(y|ic))?)\b"
```

## Confidence Scoring

Extraction functions return confidence scores for each finding:

**Scoring rules:**

- Base confidence: 0.5 (if the primary pattern matches)
- A supporting pattern: +0.1 each (max +0.4)
- Negation pattern: -0.3 each

**Example:**

```
Text: "Patient intubated with video laryngoscopy"

Primary pattern (intubat): 0.5
Supporting pattern (video laryngosc): +0.1
Final confidence: 0.6
```

**Low confidence indicates:**

- Ambiguous documentation
- Possible false positive
- Text may need manual review

## Testing Patterns

Run the test suite after modifying patterns:

```bash
# Format code
ruff format src/case_parser/patterns/

# Run linting
ruff check src/case_parser/patterns/

# Test with sample data
python main.py test_input.xlsx test_output.xlsx --validation-report validation.txt
```

## Adding a New Extraction Category

To add a completely new extraction category:

1. **Create pattern file:** `patterns/new_category_patterns.py`

   ```python
   """New Category Extraction Patterns."""

   from __future__ import annotations
   from typing import Any
   import pandas as pd

   from ..domain import NewCategory, ExtractionFinding
   from .extraction_utils import extract_with_context, calculate_pattern_confidence

   # Define patterns
   NEW_PATTERNS = [r"\bpattern1\b", r"\bpattern2\b"]

   # Define extraction function
   def extract_new_category(notes: Any, source_field: str = "procedure_notes"):
       # Implementation here
       pass
   ```

2. **Update `__init__.py`:**

   ```python
   from .new_category_patterns import NEW_PATTERNS, extract_new_category

   __all__ = [
       # ... existing exports
       "NEW_PATTERNS",
       "extract_new_category",
   ]
   ```

3. **Update processor:** Import and use the new extraction function

4. **Add tests:** Test with sample data and verify extraction

## Questions?

If you're unsure about a pattern:

1. Check existing patterns for similar cases
2. Run the debug script to see what's currently matching
3. Test your pattern in isolation with regex testers
4. Review the extraction function to understand the logic
