"""Project-wide pytest fixtures and environment setup.

Disable AnySearch CLI auto-registration during tests by default so test fixtures
that mock a single provider do not accidentally fall back to a second
provider. Tests that explicitly exercise AnySearch can override this with
`monkeypatch.delenv("ANYSEARCH_DISABLED", raising=False)`.
"""
import os

os.environ.setdefault("ANYSEARCH_DISABLED", "1")
