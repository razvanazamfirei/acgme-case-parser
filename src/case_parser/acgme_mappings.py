"""ACGME form field mappings and lookup tables."""

from __future__ import annotations

from dataclasses import dataclass

# Patient Age Category Mappings
PATIENT_AGE_MAPPINGS: dict[str, str] = {
    "a. < 3 months": "30",
    "b. >= 3 mos. and < 3 yr.": "31",
    "c. >= 3 yr. and < 12 yr.": "32",
    "d. >= 12 yr. and < 65 yr.": "33",
    "e. >= 65 year": "34",
}

# Procedure Code Mappings (ASA Physical Status)
ASA_STATUS_CODES: dict[str, str] = {
    "1": "156628",
    "2": "156632",
    "3": "156634",
    "4": "156636",
    "5": "156630",
    "6": "156631",
    "1E": "156629",
    "2E": "156633",
    "3E": "156635",
    "4E": "156637",
    "5E": "156626",
}

# Anesthesia Type Codes
ANESTHESIA_TYPE_CODES: dict[str, str] = {
    "CSE": "156646",  # Combined Spinal-Epidural
    "Epidural": "1256332",
    "General Maintenance": "1256330",
    "MAC &/or Sedation": "156641",
    "Spinal": "1256331",
    "Peripheral Nerve Block Continuous": "156647",
    "Peripheral Nerve Block Single Shot": "156648",
}

# Airway Management Codes
AIRWAY_MANAGEMENT_CODES: dict[str, str] = {
    "Supraglottic Airway": "1256333",
    "Laryngoscope - Direct": "1256334",
    "Laryngoscope - Indirect": "1256335",
    "Oral ETT": "156654",
    "Nasal ETT": "156655",
    "Flexible Bronchoscopic": "2298046",
    "Awake Intubation": "2298047",
    "Bronchial Blocker": "156674",
    "DLT": "1256336",
    "Airway Management - Other": "1256337",
    "Jet Ventilation": "156666",
    "Mask": "156650",
}

# Procedure Category Codes
PROCEDURE_CATEGORY_CODES: dict[str, str] = {
    "Cardiac without CPB": "156682",
    "Cardiac with CPB": "156681",
    "Procedures on major vessels (endovascular)": "156685",
    "Procedures on major vessels (open)": "156684",
    "Intracerebral (endovascular)": "156688",
    "Intracerebral Nonvascular (open)": "156689",
    "Intracerebral Vascular (open)": "156687",
    "Cesarean Section": "156692",
    "Cesarean Section High-Risk": "156686",
    "Vaginal Delivery": "156690",
    "Vaginal Delivery High-Risk": "156691",
    "Intrathoracic non-cardiac": "156683",
}

# Vascular Access Codes
VASCULAR_ACCESS_CODES: dict[str, str] = {
    "Arterial Catheter": "1256338",
    "Central Venous Catheter": "1256339",
    "Pulmonary Artery Catheter": "156700",
    "Ultrasound used for line placement": "156693",
}

# Monitoring Codes
MONITORING_CODES: dict[str, str] = {
    "CSF Drain": "1256341",
    "Electrophysiologic monitoring (SSEP, MEP, EMG, EEG)": "156708",
    "Transesophageal Echo (TEE)": "156707",
}

# Neuraxial Blockade Site Codes
NEURAXIAL_SITE_CODES: dict[str, str] = {
    "Caudal": "156723",
    "Cervical": "156719",
    "Lumbar": "156722",
    "T 1-7": "156720",
    "T 8-12": "156721",
}

# Peripheral Nerve Block Site Codes
PERIPHERAL_NERVE_CODES: dict[str, str] = {
    "Adductor Canal": "1911477",
    "Ankle": "156730",
    "Axillary": "156734",
    "Erector Spinae Plane": "1911478",
    "Femoral": "156735",
    "Infraclavicular": "156732",
    "Interscalene": "156731",
    "Lumbar Plexus": "156737",
    "Paravertebral": "156739",
    "Popliteal": "156729",
    "Quadratus Lumborum": "1911476",
    "Retrobulbar": "156738",
    "Saphenous": "156740",
    "Sciatic": "156736",
    "Supraclavicular": "156733",
    "Transverse Abdominal Plane": "1911475",
    "Other - peripheral nerve blockade site": "1256340",
}

# Life-Threatening Pathology Case Type Codes
LIFE_THREATENING_CODES: dict[str, str] = {
    "Non-Trauma Life-Threatening Pathology": "46",
    "Trauma Life-Threatening Pathology": "134",
}

# Difficult Airway Case Type Codes
DIFFICULT_AIRWAY_CODES: dict[str, str] = {
    "Anticipated": "148",
    "Unanticipated": "149",
}

# Site/Institution Mappings (Example - Penn Medicine sites)
INSTITUTION_MAPPINGS: dict[str, str] = {
    "Children's Hospital of Philadelphia": "12763",
    "Pennsylvania Hospital (UPHS)": "12771",
    "Presbyterian Medical Center (UPHS)": "12871",
    "University of Pennsylvania Health System": "12748",
    "Other Site": "19367",
}

# Procedure Group Mappings
PROCEDURE_GROUP_CODES: dict[str, str] = {
    "Procedures": "681",
    "Pain Consultations and Procedures": "680",
}


@dataclass
class ProcedureCodeMapping:
    """Mapping between procedure text and ACGME code."""

    text: str
    code: str
    category: str
    area: str


class ACGMEFieldMapper:
    """Maps case-parser output to ACGME form fields."""

    def __init__(self):
        """Initialize mapper with all code mappings."""
        self.patient_age_map = PATIENT_AGE_MAPPINGS
        self.asa_codes = ASA_STATUS_CODES
        self.anesthesia_codes = ANESTHESIA_TYPE_CODES
        self.airway_codes = AIRWAY_MANAGEMENT_CODES
        self.procedure_codes = PROCEDURE_CATEGORY_CODES
        self.vascular_codes = VASCULAR_ACCESS_CODES
        self.monitoring_codes = MONITORING_CODES
        self.neuraxial_codes = NEURAXIAL_SITE_CODES
        self.peripheral_codes = PERIPHERAL_NERVE_CODES
        self.institution_map = INSTITUTION_MAPPINGS

    def get_patient_age_code(self, age_category: str) -> str | None:
        """Get ACGME patient age code from category text."""
        return self.patient_age_map.get(age_category)

    def get_institution_code(self, institution_name: str) -> str | None:
        """Get ACGME institution code from name."""
        return self.institution_map.get(institution_name)

    def parse_asa_status(self, asa_text: str) -> str | None:
        """Extract ASA code from text like 'ASA 2' or '2E'."""
        if not asa_text:
            return None

        # Clean up the text
        asa_clean = asa_text.strip().upper()

        # Try direct lookup
        if asa_clean in self.asa_codes:
            return self.asa_codes[asa_clean]

        # Try extracting from 'ASA X' format
        if asa_clean.startswith("ASA"):
            code_part = asa_clean.replace("ASA", "").strip()
            return self.asa_codes.get(code_part)

        return None

    def get_procedure_codes(self, procedures_text: str) -> list[str]:
        """
        Parse procedure descriptions and return ACGME codes.

        Args:
            procedures_text: Semicolon-separated procedure descriptions

        Returns:
            List of ACGME procedure codes
        """
        if not procedures_text:
            return []

        codes = []
        procedures = [p.strip() for p in procedures_text.split(";") if p.strip()]

        for proc in procedures:
            # Try all mapping dictionaries
            for mapping_dict in [
                self.anesthesia_codes,
                self.airway_codes,
                self.procedure_codes,
                self.vascular_codes,
                self.monitoring_codes,
                self.neuraxial_codes,
                self.peripheral_codes,
            ]:
                if proc in mapping_dict:
                    codes.append(mapping_dict[proc])
                    break

        return codes

    def fuzzy_match_institution(self, name: str) -> str | None:
        """
        Fuzzy match institution name to code.

        Args:
            name: Institution name to match

        Returns:
            ACGME institution code or None
        """
        if not name:
            return None

        name_lower = name.lower()

        # Try exact match first
        for inst_name, code in self.institution_map.items():
            if inst_name.lower() == name_lower:
                return code

        # Try partial match
        for inst_name, code in self.institution_map.items():
            if name_lower in inst_name.lower() or inst_name.lower() in name_lower:
                return code

        return None


# Create singleton instance
field_mapper = ACGMEFieldMapper()
