from inspect_ai._util.error import pip_dependency_error


def ensure_filesystem_dependencies(location: str) -> None:
    if location.startswith("hf://"):
        global _hf_initialized
        if not _hf_initialized:
            try:
                import os
                import warnings

                # disable progress bars
                os.environ["TQDM_DISABLE"] = "1"
                os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"

                # ensure hf:// filesystem is registered
                import huggingface_hub  # noqa: F401

                # when UPath falls back to fsspec it warns
                warnings.filterwarnings(
                    "ignore",
                    message=".*UPath 'hf' filesystem not explicitly implemented.*",
                )
            except ImportError:
                # let user know they need to install huggingface_hub
                raise pip_dependency_error(
                    "HuggingFace Filesystem (hf://)", ["huggingface_hub"]
                ) from None
            _hf_initialized = True


_hf_initialized = False
