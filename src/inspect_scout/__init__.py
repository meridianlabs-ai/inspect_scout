from inspect_ai._util.deprecation import relocated_module_attribute
from inspect_ai.event import (
    Timeline,
    TimelineBranch,
    TimelineEvent,
    TimelineSpan,
    timeline_build,
    timeline_dump,
    timeline_filter,
    timeline_load,
)

from ._grep_scanner import grep_scanner
from ._llm_scanner import (
    Answer,
    AnswerMultiLabel,
    AnswerSpec,
    AnswerStructured,
    ResultReducer,
    answer_type,
    generate_answer,
    llm_scanner,
    parse_answer,
    scanner_prompt,
)
from ._observe import ObserveEmit, ObserveProvider, observe, observe_update
from ._project import ProjectConfig
from ._query.condition import Condition
from ._recorder.recorder import (
    ScanResultsArrow,
    ScanResultsDF,
    Status,
)
from ._recorder.summary import Summary
from ._scan import (
    scan,
    scan_complete,
    scan_resume,
)
from ._scanjob import ScanJob, scanjob
from ._scanjob_config import ScanJobConfig
from ._scanlist import scan_list
from ._scanner.extract import (
    MessageFormatOptions,
    MessagesPreprocessor,
    message_numbering,
    messages_as_str,
    tool_callers,
)
from ._scanner.loader import Loader, loader
from ._scanner.result import Error, Reference, Result
from ._scanner.scanner import Scanner, scanner
from ._scanner.scorer import as_scorer
from ._scanner.types import ScannerInput
from ._scanresults import (
    scan_results_arrow,
    scan_results_df,
    scan_status,
)
from ._scanspec import (
    ScannerSpec,
    ScanOptions,
    ScanRevision,
    ScanSpec,
    ScanTranscripts,
    TranscriptField,
    Worklist,
)
from ._transcript.columns import Column, Columns, columns
from ._transcript.database.database import TranscriptsDB
from ._transcript.database.factory import transcripts_db
from ._transcript.database.schema import transcripts_db_schema
from ._transcript.factory import transcripts_from
from ._transcript.log import LogColumns, log_columns
from ._transcript.messages import (
    MessagesSegment,
    segment_messages,
    span_messages,
    transcript_messages,
)
from ._transcript.sample_metadata import SampleMetadata
from ._transcript.timeline import (
    TimelineMessages,
    timeline_messages,
)
from ._transcript.transcripts import ScannerWork, Transcripts, TranscriptsReader
from ._transcript.types import (
    EventType,
    MessageType,
    Transcript,
    TranscriptContent,
    TranscriptInfo,
)
from ._util.refusal import RefusalError
from ._validation import (
    PredicateFn,
    PredicateType,
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
    # observe
    "observe",
    "observe_update",
    "ObserveEmit",
    "ObserveProvider",
    # scan
    "scan",
    "scan_resume",
    "scan_complete",
    "ScanSpec",
    "ScanOptions",
    "ScannerSpec",
    "ScannerWork",
    "Worklist",
    "ScanRevision",
    "ScanTranscripts",
    "TranscriptField",
    "scanjob",
    "ScanJob",
    "ScanJobConfig",
    "ProjectConfig",
    "scan_list",
    "scan_status",
    "scan_results_df",
    "Status",
    "ScanResultsDF",
    "scan_results_arrow",
    "ScanResultsArrow",
    "Summary",
    # transcript
    "transcripts_db",
    "TranscriptsDB",
    "transcripts_db_schema",
    "transcripts_from",
    "Transcripts",
    "TranscriptsReader",
    "Transcript",
    "TranscriptInfo",
    "Column",
    "Condition",
    "Columns",
    "columns",
    "LogColumns",
    "log_columns",
    "SampleMetadata",
    # timeline
    "Timeline",
    "TimelineBranch",
    "TimelineEvent",
    "TimelineMessages",
    "TimelineSpan",
    "timeline_build",
    "timeline_dump",
    "timeline_filter",
    "timeline_load",
    "timeline_messages",
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
    "TranscriptContent",
    "as_scorer",
    "message_numbering",
    "messages_as_str",
    "span_messages",
    "segment_messages",
    "MessagesSegment",
    "transcript_messages",
    "MessageFormatOptions",
    "MessagesPreprocessor",
    "tool_callers",
    "RefusalError",
    "llm_scanner",
    "ResultReducer",
    "Answer",
    "AnswerMultiLabel",
    "AnswerSpec",
    "AnswerStructured",
    "answer_type",
    "generate_answer",
    "parse_answer",
    "scanner_prompt",
    "grep_scanner",
    # validation
    "ValidationSet",
    "ValidationCase",
    "ValidationPredicate",
    "PredicateType",
    "PredicateFn",
    "validation_set",
    # version
    "__version__",
]


_DEPRECATED_VERSION_2_2 = "0.2.2"
_REMOVED_IN = "0.3"
relocated_module_attribute(
    "scan_results",
    "inspect_scout.scan_results_df",
    _DEPRECATED_VERSION_2_2,
    _REMOVED_IN,
)


relocated_module_attribute(
    "transcripts_from_logs",
    "inspect_scout.transcripts_from",
    _DEPRECATED_VERSION_2_2,
    _REMOVED_IN,
)


_DEPRECATED_VERSION_4_2 = "0.4.2"
relocated_module_attribute(
    "Metadata",
    "inspect_scout.Columns",
    _DEPRECATED_VERSION_4_2,
    _REMOVED_IN,
)

relocated_module_attribute(
    "metadata",
    "inspect_scout.columns",
    _DEPRECATED_VERSION_4_2,
    _REMOVED_IN,
)

relocated_module_attribute(
    "LogMetadata",
    "inspect_scout.LogColumns",
    _DEPRECATED_VERSION_4_2,
    _REMOVED_IN,
)

relocated_module_attribute(
    "log_metadata",
    "inspect_scout.log_columns",
    _DEPRECATED_VERSION_4_2,
    _REMOVED_IN,
)
