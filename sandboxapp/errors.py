from uengine.errors import NotFound, ApiError, IntegrityError


class InvalidUserId(NotFound):
    error_key = "invalid_user_id"

    def __init__(self, user_id):
        super().__init__(f"invalid user_id ({user_id}) or user not found", payload={"user_id": user_id})


class InvalidPassword(ApiError):
    error_key = "invalid_password"
    pass


class NotEmpty(IntegrityError):
    error_key = "model.not_empty"
    pass


class ChildExists(IntegrityError):
    error_key = "child_exists"
    pass


class ChildDoesNotExist(IntegrityError):
    error_key = "child_doesnt_exists"
    pass


class ParentExists(IntegrityError):
    error_key = "parent_exists"
    pass


class ParentDoesNotExist(IntegrityError):
    error_key = "parent_doesnt_exists"
    pass


class ParentCycle(IntegrityError):
    error_key = "parent_cycle"
    pass


class InvalidWorkGroup(IntegrityError):
    error_key = "work_group.invalid"
    pass


class InvalidFQDN(ApiError):
    error_key = "host.invalid_fqdn"
    pass


class InvalidAlias(InvalidFQDN):
    error_key = "host.invalid_alias"
    pass


class InvalidTags(ApiError):
    error_key = "invalid_tags"
    pass


class InvalidExtId(ApiError):
    error_key = "host.invalid_ext_id"
    pass


class InvalidNetworkInterfaces(ApiError):
    error_key = "host.invalid_network_interfaces"
    pass


class InvalidProvisionState(ApiError):
    error_key = "host.invalid_provision_state"
    pass


class InvalidRelocation(ApiError):
    error_key = "host.invalid_relocation"
    pass


class UserHasReferences(IntegrityError):
    error_key = "user.has_references"
    pass


class OutOfBounds(ApiError):
    error_key = "out_of_bounds"
    pass


class MergeError(IntegrityError):
    error_key = "merge_error"
    pass
