from inspect_ai._util.deprecation import relocated_module_attribute

from ._llm_scanner import AnswerMultiLabel, AnswerStructured, llm_scanner
from ._recorder.recorder import (
    ScanResultsDF,
    Status,
)
from ._recorder.summary import Summary
from ._scan import (
    scan,
    scan_complete,
    scan_resume,
)
from ._scanjob import ScanJob, ScanJobConfig, scanjob
from ._scanlist import scan_list
from ._scanner.extract import MessagesPreprocessor, messages_as_str
from ._scanner.loader import Loader, loader
from ._scanner.result import Error, Reference, Result
from ._scanner.scanner import Scanner, scanner
from ._scanner.scorer import as_scorer
from ._scanner.types import ScannerInput
from ._scanresults import (
    scan_results_df,
    scan_status,
)
from ._scanspec import (
    ScannerSpec,
    ScannerWork,
    ScanOptions,
    ScanRevision,
    ScanSpec,
    ScanTranscripts,
    TranscriptField,
)
from ._transcript.database import transcripts_from_logs
from ._transcript.log import LogMetadata, log_metadata
from ._transcript.metadata import Column, Condition, Metadata, metadata
from ._transcript.transcripts import Transcripts
from ._transcript.types import (
    EventType,
    MessageType,
    Transcript,
    TranscriptInfo,
)
from ._util.refusal import RefusalError
from ._validation import (
    ValidationCase,
    ValidationPredicate,
    ValidationSet,
    validation_set,
)

try:
    from ._version import __version__
except ImportError:
    __version__ = "unknown"


__all__ = [
    # scan
    "scan",
    "scan_resume",
    "scan_complete",
    "ScanSpec",
    "ScanOptions",
    "ScannerSpec",
    "ScannerWork",
    "ScanRevision",
    "ScanTranscripts",
    "TranscriptField",
    "scanjob",
    "ScanJob",
    "ScanJobConfig",
    # results
    "scan_list",
    "scan_status",
    "scan_results_df",
    "Status",
    "ScanResultsDF",
    "Summary",
    # transcript
    "transcripts_from_logs",
    "Transcripts",
    "Transcript",
    "TranscriptInfo",
    "Column",
    "Condition",
    "Metadata",
    "metadata",
    "LogMetadata",
    "log_metadata",
    # scanner
    "Error",
    "Scanner",
    "ScannerInput",
    "Result",
    "Reference",
    "scanner",
    "Loader",
    "loader",
    "EventType",
    "MessageType",
    "as_scorer",
    "messages_as_str",
    "MessagesPreprocessor",
    "RefusalError",
    # llm_scanner
    "llm_scanner",
    "AnswerMultiLabel",
    "AnswerStructured",
    # validation
    "ValidationSet",
    "ValidationCase",
    "ValidationPredicate",
    "validation_set",
    # version
    "__version__",
]


_SCAN_RESULTS_VERSION_2_2 = "0.2.2"
_REMOVED_IN = "0.3"
relocated_module_attribute(
    "scan_results",
    "inspect_scout.scan_results_df",
    _SCAN_RESULTS_VERSION_2_2,
    _REMOVED_IN,
)
