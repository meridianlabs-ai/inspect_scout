from pathlib import Path

from inspect_scout import ScanJobConfig, scan
from inspect_scout._scanspec import ScanScanner

if __name__ == "__main__":
    parent = Path(__file__).parent

    config = ScanJobConfig(
        scanners=[
            ScanScanner(name="deception", file=(parent / "scanner.py").as_posix()),
            ScanScanner(
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
