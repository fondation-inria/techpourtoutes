from .base import BaseService

TRANSIENT_CODES = frozenset({429})
FIRST_SERVER_ERROR_CODE = 500


class BaseApiService(BaseService):
    """A service whose failures can come from an external API, and travel upwards.

    Two families inherit from it: the services that talk to an API, which set `status_code`
    or `network_error` themselves, and the orchestrators that only relay their failure
    through `fail_with_errors` without ever inspecting it.
    """

    status_code: int | None = None
    network_error: bool = False

    def fail_with_errors(self, result: BaseApiService) -> None:
        """Adopt another service's failure: its messages, and what makes it retryable."""
        self.status_code = result.status_code
        self.network_error = result.network_error
        self.fail(", ".join(result.errors))

    def failed_with_transient_error(self) -> bool:
        """No answer at all, rate limiting, or a server-side error: worth trying again."""
        if self.network_error:
            return True
        if self.status_code is None:
            return False
        return self.status_code in TRANSIENT_CODES or self.status_code >= FIRST_SERVER_ERROR_CODE
