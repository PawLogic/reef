"""Describe the actual episode scorer without changing how it scores."""

from __future__ import annotations

import inspect

from reef.harness.tree.nodes import clip_record_text, redact_secret_shaped


def scoring_rule(scorer: object) -> dict[str, str]:
    """Capture the scorer implementation at evaluation time, not when a historical page is viewed."""
    implementation = type(scorer)
    result = {"implementation": f"{implementation.__module__}:{implementation.__qualname__}"}
    description = inspect.getdoc(implementation)
    if description:
        result["description"] = redact_secret_shaped(description)
    try:
        source = inspect.getsource(implementation)
    except (OSError, TypeError):
        result["source_status"] = "Source is unavailable for this scorer."
    else:
        result["source"] = clip_record_text(redact_secret_shaped(source))
    return result
