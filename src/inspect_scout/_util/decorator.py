def split_spec(spec: str) -> tuple[str, str | None]:
    parts = spec.rsplit("@", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    else:
        return spec, None
