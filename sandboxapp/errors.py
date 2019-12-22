from uengine.errors import NotFound, ApiError


class InvalidUserId(NotFound):
    error_key = "invalid_user_id"

    def __init__(self, user_id):
        super().__init__(f"invalid user_id ({user_id}) or user not found", payload={"user_id": user_id})

