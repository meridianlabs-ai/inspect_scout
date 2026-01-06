from pathlib import Path

from inspect_scout import scan
from inspect_scout._scanjob_config import ScanJobConfig
from inspect_scout._scanspec import ScannerSpec

if __name__ == "__main__":
    parent = Path(__file__).parent

    config = ScanJobConfig(
        scanners=[
            ScannerSpec(name="deception", file=(parent / "scanner.py").as_posix()),
            ScannerSpec(
                name="target_word_scanner",
                file=(parent / "scanner.py").as_posix(),
                params={"target_word": "perfect"},
            ),
        ],
        transcripts=(parent / "logs").as_posix(),
        max_transcripts=15,
        max_processes=5,
    )

    scan(config)
