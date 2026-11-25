import re

from modules.ia.core.errors import ArtifactTrustError

SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")

APPROVAL_SEPARATORS = re.compile(r"[\s,;]+")


def parse_approved_scaler_digests(raw: str | None) -> frozenset[str]:
    """Parse AI_APPROVED_SCALER_SHA256 into normalized SHA-256 digests.

    Accepts commas, semicolons, spaces or newlines as separators, optional
    quotes, and uppercase hex (PowerShell ``Get-FileHash`` prints uppercase).
    Any entry that is not a SHA-256 digest is rejected instead of being
    silently ignored, so a malformed approval list is visible at startup.
    """
    digests = set()
    invalid = []
    for token in APPROVAL_SEPARATORS.split(raw or ""):
        token = token.strip().strip("'\"").lower()
        if not token:
            continue
        if SHA256_PATTERN.fullmatch(token):
            digests.add(token)
        else:
            invalid.append(token[:16] + ("…" if len(token) > 16 else ""))
    if invalid:
        raise ArtifactTrustError(
            "AI_APPROVED_SCALER_SHA256 contains values that are not SHA-256 digests: "
            + ", ".join(invalid)
        )
    return frozenset(digests)
