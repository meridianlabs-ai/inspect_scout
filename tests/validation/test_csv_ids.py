"""CSV validation identifiers retain their source representation."""

import asyncio
import csv
import json
from pathlib import Path

import pytest
from inspect_ai.model import ChatMessageUser
from inspect_scout import (
    Result,
    Scanner,
    Transcript,
    scan,
    scan_results_df,
    scanner,
    transcripts_db,
    transcripts_from,
    validation_set,
)
from inspect_scout._validation.writer import ValidationFileWriter


@pytest.mark.parametrize("headerless", [False, True])
@pytest.mark.parametrize(
    "case_id", ["001", "1e3", "1.0", "NA", "NULL", "N/A", "NaN", "true", "task-1", "雪"]
)
def test_csv_preserves_id(tmp_path: Path, case_id: str, headerless: bool) -> None:
    path = tmp_path / "cases.csv"
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        if not headerless:
            writer.writerow(["id", "target"])
        writer.writerow([case_id, "true"])
        writer.writerow([case_id, "false"])

    cases = validation_set(path).cases
    assert [case.id for case in cases] == [case_id, case_id]
    assert cases[0].target is True
    assert cases[1].target is False


@pytest.mark.parametrize("headerless", [False, True])
@pytest.mark.parametrize("array", [False, True])
def test_csv_id_lists(tmp_path: Path, headerless: bool, array: bool) -> None:
    path = tmp_path / "cases.csv"
    ids = ["001", "NA", "NULL"]
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        if not headerless:
            writer.writerow(["id", "target"])
        writer.writerow([json.dumps(ids) if array else ",".join(ids), "true"])
    assert validation_set(path).cases[0].id == ids


def test_csv_reordered_columns_and_quoted_newlines(tmp_path: Path) -> None:
    path = tmp_path / "cases.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["target", "id", "split"])
        writer.writerow(["true", "001\nNA", ""])
        writer.writerow([])
        writer.writerow(["false", "NULL", "test"])
    cases = validation_set(path).cases
    assert [case.id for case in cases] == ["001\nNA", "NULL"]
    assert [case.split for case in cases] == [None, "test"]
    assert cases[0].target is True
    assert cases[1].target is False


@pytest.mark.parametrize("case_id", ["001", "NA", "NULL", "task-1"])
def test_csv_writer_round_trip_preserves_id(tmp_path: Path, case_id: str) -> None:
    path = tmp_path / "cases.csv"
    path.write_text(f"id,target,split\n{case_id},true,\n")
    writer = ValidationFileWriter(path)
    for _ in range(2):
        cases = writer.read_cases()
        assert cases == [{"id": case_id, "target": True}]
        writer.write_cases(cases)
        assert validation_set(path).cases[0].id == case_id


def test_csv_target_inference_is_preserved(tmp_path: Path) -> None:
    path = tmp_path / "cases.csv"
    path.write_text(
        "id,target_boolean,target_number,split\n001,true,42,\nNA,false,1.5,test\n"
    )
    cases = validation_set(path).cases
    assert [case.id for case in cases] == ["001", "NA"]
    assert cases[0].target == {"boolean": True, "number": 42}
    assert cases[1].target == {"boolean": False, "number": 1.5}
    assert [case.split for case in cases] == [None, "test"]


@scanner(messages="all")
def csv_id_scanner() -> Scanner[Transcript]:
    async def scan(transcript: Transcript) -> Result:
        return Result(value=True)

    return scan


def test_csv_cases_match_transcripts(tmp_path: Path) -> None:
    ids = ["001", "NA", "NULL"]
    database = str(tmp_path / "transcripts")

    async def populate() -> None:
        async with transcripts_db(database) as db:
            await db.insert(
                [
                    Transcript(
                        transcript_id=case_id,
                        messages=[ChatMessageUser(content="Hello")],
                    )
                    for case_id in ids
                ]
            )

    asyncio.run(populate())
    path = tmp_path / "cases.csv"
    path.write_text("id,target\n" + "".join(f"{case_id},true\n" for case_id in ids))
    status = scan(
        scanners=[csv_id_scanner()],
        transcripts=transcripts_from(database),
        validation=str(path),
        scans=str(tmp_path / "scans"),
        max_processes=1,
        display="none",
    )
    assert status.complete
    assert not status.errors
    results = scan_results_df(status.location).scanners["csv_id_scanner"]
    assert set(results["transcript_id"]) == set(ids)
    assert results["validation_result"].tolist() == ["true"] * len(ids)
