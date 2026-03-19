class BaseAppException(Exception):
    status_code = 400
    detail = "Bad request"

    def __init__(self, detail: str | None = None) -> None:
        if detail is not None:
            self.detail = detail
        super().__init__(self.detail)

    def __str__(self) -> str:
        return self.__class__.__name__


class NotFoundError(BaseAppException):
    status_code = 404
    detail = "Not found"


class ForbiddenError(BaseAppException):
    status_code = 403
    detail = "Forbidden"


class ConflictError(BaseAppException):
    status_code = 409
    detail = "Conflict"


class BadRequestError(BaseAppException):
    status_code = 400
    detail = "Bad request"


class UnauthorizedError(BaseAppException):
    status_code = 401
    detail = "Unauthorized"
