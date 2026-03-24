Welcome to Inspect Scout.

To get started with Inspect Scout, please see the [documentation](https://meridianlabs-ai.github.io/inspect_scout/).

***

## Installation

Latest development version:

```bash
pip install git+https://github.com/meridianlabs-ai/inspect_scout
```

## Development

To work on development of Inspect Scout, clone the repository and install with the `-e` flag and `[dev]` optional dependencies:

```bash
git clone https://github.com/meridianlabs-ai/inspect_scout
cd inspect_scout
pip install -e ".[dev]"
```

Run linting, formatting, and tests via

```bash
make check
make test
```

### Frontend development (TypeScript)

The web UI lives in a git submodule and uses Git LFS for binary assets. **These steps are only needed if you plan to work on the TypeScript/React frontend** — Python-only contributors can skip this entirely.

1. [Install Git LFS](https://git-lfs.com/) and run `git lfs install`
2. Initialize the submodule and install dependencies — see the [one-time setup guide](src/inspect_scout/_view/ts-mono/docs/submodule-guide.md#one-time-setup)


