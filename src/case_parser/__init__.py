"""Case Parser - A tool for processing anesthesia case data from Excel files."""

from .acgme_mappings import ACGMEFieldMapper
from .cli import main
from .domain import (
    AgeCategory,
    AirwayManagement,
    AnesthesiaType,
    MonitoringTechnique,
    ParsedCase,
    ProcedureCategory,
    VascularAccess,
)
from .enhanced_processor import EnhancedCaseProcessor
from .io import ExcelHandler
from .models import AgeRange, ColumnMap, ProcedureRule
from .processors import CaseProcessor
from .validation import ValidationReport
from .web_exporter import WebExporter, export_cases_to_json

__version__ = "0.1.0"
__all__ = [
    "ACGMEFieldMapper",
    "AgeCategory",
    "AgeRange",
    "AirwayManagement",
    "AnesthesiaType",
    "CaseProcessor",
    "ColumnMap",
    "EnhancedCaseProcessor",
    "ExcelHandler",
    "MonitoringTechnique",
    "ParsedCase",
    "ProcedureCategory",
    "ProcedureRule",
    "ValidationReport",
    "VascularAccess",
    "WebExporter",
    "export_cases_to_json",
    "main",
]
