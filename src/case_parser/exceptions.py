"""Custom exceptions for the case parser."""


class CaseParserError(Exception):
    """Base exception for case parser errors."""


class DataValidationError(CaseParserError):
    """Raised when input data validation fails."""


class FileProcessingError(CaseParserError):
    """Raised when file processing fails."""


class ConfigurationError(CaseParserError):
    """Raised when configuration is invalid."""
