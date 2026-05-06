class FailedServiceError(Exception):
    pass


class BaseService:
    def __init__(self, **kwargs):
        self.errors: list[str] = []
        try:
            self.perform(**kwargs)
        except FailedServiceError as exc:
            message = str(exc)
            if message:
                self.errors.append(message)
        self.success = not self.errors
        self.failure = bool(self.errors)

    def perform(self, **kwargs) -> None:
        raise NotImplementedError

    def fail(self, error_message: str | None = None) -> None:
        raise FailedServiceError(error_message or "")
