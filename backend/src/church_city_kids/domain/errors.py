"""Domain errors. Messages must not include personal data."""


class DomainError(Exception):
    """Base type for domain rule violations."""


class ChildInactiveError(DomainError):
    def __init__(self) -> None:
        super().__init__("Child is inactive.")


class FamilyInactiveError(DomainError):
    def __init__(self) -> None:
        super().__init__("Family is inactive.")


class FamilyMismatchError(DomainError):
    def __init__(self) -> None:
        super().__init__("Child does not belong to the given family.")


class SessionNotOpenError(DomainError):
    def __init__(self) -> None:
        super().__init__("Session is not open.")


class ChildAgeOutOfRangeError(DomainError):
    def __init__(self) -> None:
        super().__init__("Child age is outside the session age range.")


class ChildAlreadyCheckedInError(DomainError):
    def __init__(self) -> None:
        super().__init__("Child already has an active attendance.")


class AttendanceAlreadyCheckedOutError(DomainError):
    def __init__(self) -> None:
        super().__init__("Attendance is already checked out.")


class DuplicateChildGuardianError(DomainError):
    def __init__(self) -> None:
        super().__init__("Guardian is already linked to this child.")


class InvalidAgeRangeError(DomainError):
    def __init__(self) -> None:
        super().__init__("Session age range is invalid.")


class InvalidServiceScheduleError(DomainError):
    def __init__(self) -> None:
        super().__init__("Service end must be after start.")


class RoomAlreadyAssignedInServiceError(DomainError):
    def __init__(self) -> None:
        super().__init__("Room is already used by another session in this service.")


class VolunteerAlreadyAssignedInServiceError(DomainError):
    def __init__(self) -> None:
        super().__init__("Volunteer is already assigned to a session in this service.")


class PagerInactiveError(DomainError):
    def __init__(self) -> None:
        super().__init__("Pager is inactive.")


class AttendanceNotActiveError(DomainError):
    def __init__(self) -> None:
        super().__init__("Attendance is not active.")


class PagerAlreadyAssignedError(DomainError):
    def __init__(self) -> None:
        super().__init__("Pager is already assigned.")


class AttendanceAlreadyHasPagerError(DomainError):
    def __init__(self) -> None:
        super().__init__("Attendance already has an active pager assignment.")
