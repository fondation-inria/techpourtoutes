from enum import StrEnum


class FailedServiceError(Exception):
    pass


class ErrorKind(StrEnum):
    """What kind of failure a service hit, so its caller knows whether to try again."""

    PERMANENT = "permanent"
    TRANSIENT = "transient"


class BaseService:
    """Base class for service objects.

    Encapsulates a single procedural operation with a clear success/failure state.
    Subclasses implement `perform(**kwargs)`, which is called automatically on
    instantiation with the kwargs passed to the constructor.

    Usage:
        result = MyService(foo=bar)
        if result.success:
            ...
        else:
            ...
            (result.errors is a list of human-readable error strings)

    To signal failure from within `perform`, call `self.fail("message")`, which raises
    `FailedServiceError` and stops execution. The error is caught and appended to
    `self.errors`; `self.success` is then False and `self.failure` is True.
    """

    error_kind: ErrorKind = ErrorKind.PERMANENT

    def __init__(self, **kwargs):
        self.errors: list[str] = []
        try:
            self.perform(**kwargs)
        except FailedServiceError as exc:
            self.errors.append(str(exc))
        self.success = not self.errors
        self.failure = bool(self.errors)

    def perform(self, **kwargs) -> None:
        raise NotImplementedError

    @property
    def failed_with_transient_error(self) -> bool:
        """Whether trying the very same thing again could succeed."""
        return self.error_kind is ErrorKind.TRANSIENT

    def fail(self, error_message: str | None = None, *, kind=ErrorKind.PERMANENT) -> None:
        self.error_kind = kind
        raise FailedServiceError(error_message or "")

    def fail_with_errors(self, result: BaseService) -> None:
        """Adopt another service's failure: its messages, and what kind of failure it was."""
        self.fail(", ".join(result.errors), kind=result.error_kind)
