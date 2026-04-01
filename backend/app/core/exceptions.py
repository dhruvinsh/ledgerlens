class AppError(Exception):
    """Base for all domain errors."""

    def __init__(self, message: str, code: str = "APP_ERROR"):
        self.message = message
        self.code = code


class NotFoundError(AppError):
    pass


class ConflictError(AppError):
    pass


class ForbiddenError(AppError):
    pass


class ValidationError(AppError):
    pass


class AuthenticationError(AppError):
    pass


# Specific errors
class ReceiptNotFoundError(NotFoundError):
    pass


class ItemNotFoundError(NotFoundError):
    pass


class StoreNotFoundError(NotFoundError):
    pass


class JobNotFoundError(NotFoundError):
    pass


class HouseholdNotFoundError(NotFoundError):
    pass


class DuplicateEmailError(ConflictError):
    pass


class ActiveJobExistsError(ConflictError):
    pass


class InvalidCredentialsError(AuthenticationError):
    pass


class OCRProcessingError(AppError):
    pass
