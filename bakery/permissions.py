from rest_framework.permissions import BasePermission


class IsStudent(BasePermission):
    """Allows access only to authenticated users who have a StudentProfile."""

    message = "This action is only available to college students."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, "student_profile")
        )


class IsBakeryMember(BasePermission):
    """Allows access only to authenticated users who have a BakeryMemberProfile."""

    message = "This action is only available to bakery staff."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and hasattr(request.user, "bakery_profile")
        )
