class FailedServiceError(Exception):
    pass


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

    def fail(self, error_message: str | None = None) -> None:
        raise FailedServiceError(error_message or "")
