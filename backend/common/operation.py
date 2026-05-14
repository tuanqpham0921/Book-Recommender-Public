import logging
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class OperationResult:
    """Outcome of a single named check or step."""

    # TODO: might need to add other fields here like timestamp, status, etc.
    name: str
    ok: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class OperationReport:
    """Collection of operation results with aggregate pass/fail state."""

    checks: list[OperationResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(check.ok for check in self.checks)

    def get(self, name: str) -> OperationResult | None:
        return next((check for check in self.checks if check.name == name), None)

    def log(
        self,
        logger: logging.Logger | None = None,
        *,
        success_summary: str | None = None,
        check_label: str = "Check",
    ) -> None:
        """Emit per-check logs and an optional summary when all checks pass."""
        log = logger or logging.getLogger(__name__)

        for check in self.checks:
            if check.ok:
                log.debug(
                    "%s passed: %s",
                    check_label,
                    check.name,
                    extra={"details": check.details},
                )
                continue

            log.warning(
                "%s failed: %s — %s",
                check_label,
                check.name,
                check.message,
                extra={"details": check.details},
            )

        if self.ok and success_summary:
            log.info(success_summary)
