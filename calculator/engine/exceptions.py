class CalculationEngineError(Exception):
    """Base — catch this for any engine failure."""


class InputValidationError(CalculationEngineError):
    """User's CSV failed validation. Message is safe to show the user."""


class MortalityTableLoadError(CalculationEngineError):
    """Mortality table missing or malformed. Deployment/config problem."""


class MortalityTableLookupError(CalculationEngineError):
    """Employee age outside the mortality table range."""


class OutputWriteError(CalculationEngineError):
    """Output CSV could not be written to disk."""
