from . import ctx
from traceback import format_exc
from starlette.requests import Request
from starlette.responses import JSONResponse


class ApiError(Exception):

    status_code = 400
    error_key = "api_error"

    def __init__(self, message, status_code=None, payload=None):
        super().__init__(self)
        self.message = message
        if status_code:
            self.status_code = status_code

        self.payload = payload or {}

    def to_dict(self):
        data = self.payload
        data["error_key"] = self.error_key
        data["error"] = self.message
        return data

    def __repr__(self):
        return "%s: %s, status_code=%s" % (self.__class__.__name__, self.message, self.status_code)

    def __str__(self):
        return "%s, status_code=%s" % (self.message, self.status_code)


class AuthenticationError(ApiError):

    status_code = 401
    error_key = "auth_error"
    auth_url = None

    def __init__(self, message="you must be authenticated first", payload=None):
        super().__init__(message, payload=payload)
        if self.auth_url is None:
            oauth_cfg = ctx.cfg.get("oauth")
            if oauth_cfg:
                client_id = oauth_cfg.get("id")
                auth_url = oauth_cfg.get("authorize_url")
                callback_url = oauth_cfg.get("callback_url")
                if client_id and auth_url and callback_url:
                    AuthenticationError.auth_url = f"{auth_url}?response_type=code&" \
                        f"client_id={client_id}&scope=user_info&redirect_uri={callback_url}"

    def to_dict(self):
        data = super().to_dict()
        data["oauth"] = self.auth_url
        if "state" not in data:
            data["state"] = "logged out"
        return data


class Authenticated(ApiError):
    error_key = "authenticated"
    status_code = 400

    def __init__(self, *args, **kwargs):
        super().__init__("already authenticated", *args, **kwargs)


class ConfigurationError(SystemExit):
    pass


class Forbidden(ApiError):
    error_key = "forbidden"
    status_code = 403


class IntegrityError(ApiError):
    error_key = "integrity_error"
    status_code = 409


class NotFound(ApiError):
    error_key = "not_found"
    status_code = 404


class FieldRequired(ApiError):
    error_key = "field.required"
    status_code = 400

    def __init__(self, field_name):
        super().__init__(f"Field \"{field_name}\" is required", payload={"field": field_name})


class InvalidFieldType(ApiError):
    error_key = "field.invalid_type"

    def __init__(self, field_name, field_type, expected_type):
        super().__init__(f"Field \"{field_name}\" must be of type "
                         f"{expected_type.__name__}, "
                         f"got {field_type} instead",
                         payload={
                             "field": field_name,
                             "expected_type": expected_type.__name__,
                             "actual_type": field_type
                         })


class ShardIsReadOnly(IntegrityError):
    error_key = "shard.readonly"
    pass


class InvalidShardId(ApiError):
    error_key = "shard.invalid_id"
    status_code = 500


class MissingShardId(ApiError):
    error_key = "shard.missing"
    status_code = 500


class ModelDestroyed(IntegrityError):
    error_key = "model.destroyed"
    pass


class MissingSubmodel(IntegrityError):
    error_key = "submodel.missing"
    pass


class WrongSubmodel(IntegrityError):
    error_key = "submodel.wrong"
    pass


class UnknownSubmodel(IntegrityError):
    error_key = "submodel.unknown"
    pass


class InputDataError(ApiError):
    error_key = "bad_input"
    pass


async def handle_api_error(request: Request, exc: ApiError):
    content = exc.to_dict()
    content["request"] = {
        "m": request.method,
        "p": request.url.path,
        "q": request.url.query,
    }
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )


async def handle_other_errors(request: Request, exc: Exception):
    code = 400
    if hasattr(exc, "code"):
        code = exc.code
    if not (100 <= code <= 600):
        code = 400
    ctx.log.error(format_exc())

    content = {
        "error": str(exc),
        "request": {
            "m": request.method,
            "p": request.url.path,
            "q": request.url.query,
        }
    }

    return JSONResponse(
        status_code=code,
        content=content,
    )
