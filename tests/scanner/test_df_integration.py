from pathlib import Path

import pandas as pd
import pytest
from inspect_ai.analysis import samples_df
from inspect_scout import log_columns as lc
from inspect_scout._transcript.caching import samples_df_with_caching
from inspect_scout._transcript.eval_log import (
    EvalLogTranscriptsReader,
    TranscriptColumns,
)
from inspect_scout._transcript.transcripts import TranscriptsQuery

from tests.helpers import temp_kvstore

LOGS_DIR = Path(__file__).parent.parent / "recorder" / "logs"
LOG_1 = LOGS_DIR / "2025-09-23T08-09-58-04-00_popularity_DN2wbX2ZvACsBpjwptzBRo.eval"
LOG_2 = (
    LOGS_DIR / "2025-09-23T08-09-58-04-00_security-guide_LuxZJVwvymC3S3SyoJczxB.eval"
)

REFERENCE_SAMPLE_ID = "MUBxLNC9YwakjPFXaFuEZ4"
REFERENCE_EVAL_CREATED = "2025-09-23 12:09:58+00:00"
REFERENCE_WORKING_TIME = 1.201


@pytest.mark.asyncio
async def test_integration() -> None:
    """Cache roundtrip preserves realistic DataFrame with pyarrow dtypes."""

    def _sample_reader(path: str) -> pd.DataFrame:
        return samples_df([path], TranscriptColumns)

    with temp_kvstore() as kvstore_name:
        df_1 = _sample_reader(LOG_1.as_posix())

        # Put LOG_1 into the cache
        all_misses = samples_df_with_caching(_sample_reader, LOG_1, kvstore_name)
        _validate_df(all_misses)

        # Now grab LOG_1 out of the cache
        all_hits = samples_df_with_caching(_sample_reader, LOG_1, kvstore_name)
        _validate_df(all_hits)

        # Make sure that the cache didn't mess with it
        # We need check_dtype=False since the roundtrip keeps them equiv but not
        # identical. `sample_id`, for example:
        #   string[pyarrow]
        #        ->
        #   StringDtype(storage=pyarrow, na_value=<NA>)
        pd.testing.assert_frame_equal(df_1, all_hits, check_dtype=False)

        # Now ask for LOG_2 as well - causing a mix of a cache hit and a miss so
        # that the results are a concatenation between the cache hit and the freshly
        # read miss before it goes into the cache
        mixture = samples_df_with_caching(_sample_reader, [LOG_1, LOG_2], kvstore_name)
        _validate_df(mixture)

        row = mixture[mixture["sample_id"] == REFERENCE_SAMPLE_ID]
        assert row["date"].iloc[0] == pd.Timestamp(REFERENCE_EVAL_CREATED)
        assert row["working_time"].iloc[0] == REFERENCE_WORKING_TIME

        # This validates that we can properly create the in memory SQLite db
        async with EvalLogTranscriptsReader(
            mixture, TranscriptsQuery(where=[lc.sample_id == REFERENCE_SAMPLE_ID])
        ) as reader:
            t = await reader.index().__anext__()
            assert t.metadata["sample_id"] == REFERENCE_SAMPLE_ID
            assert t.metadata["date"] == REFERENCE_EVAL_CREATED
            assert t.metadata["working_time"] == REFERENCE_WORKING_TIME


def _validate_df(df: pd.DataFrame) -> None:
    # this is a little sketchy - testing implementation details, but the flow is
    # quite fragile and easy to miss if we mess it up
    assert df["date"].dtype.name == "timestamp[ns, tz=UTC][pyarrow]"
    assert df["epoch"].dtype.name == "int64[pyarrow]"
    assert df["working_time"].dtype.name == "double[pyarrow]"
