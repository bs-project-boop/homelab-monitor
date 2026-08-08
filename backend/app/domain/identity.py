def namespaced_id(source: str, local_id: str) -> str:
    """Return a globally unique ID while preserving source ownership."""
    if not source or not source.strip():
        raise ValueError("source must not be empty")
    if not local_id or not local_id.strip():
        raise ValueError("local_id must not be empty")
    return f"{source.strip()}:{local_id.strip()}"
