from .base import BaseService, ErrorKind

TRANSIENT_CODES = frozenset({429})
FIRST_SERVER_ERROR_CODE = 500


class BaseApiService(BaseService):
    """A service that talks to an external API.

    Subclasses set `status_code` or `network_error` from the response, then fail as usual —
    the kind is never declared by hand, it is read off what came back.
    """

    status_code: int | None = None
    network_error: bool = False

    def fail(self, error_message: str | None = None) -> None:
        super().fail(error_message, kind=self._error_kind())

    def _error_kind(self) -> ErrorKind:
        """No answer at all, rate limiting, or a server-side error: worth trying again."""
        if self.network_error:
            return ErrorKind.TRANSIENT
        if self.status_code is None:
            return ErrorKind.PERMANENT
        if self.status_code in TRANSIENT_CODES or self.status_code >= FIRST_SERVER_ERROR_CODE:
            return ErrorKind.TRANSIENT
        return ErrorKind.PERMANENT
