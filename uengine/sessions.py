from base64 import b64encode, b64decode
from binascii import Error as Base64Error
from datetime import datetime
from starlette.requests import Request
from itsdangerous import Signer, BadSignature
from typing import Optional, Type

from . import ctx
from .models.storable_model import StorableModel
from .utils import now, uuid4_string

_signer = None


def get_signer() -> Signer:
    global _signer
    if not _signer:
        key = ctx.cfg.get("app_secret_key")
        if not key:
            raise RuntimeError("app_secret_key not configured")
        _signer = Signer(key)
    return _signer


def generate_session_id() -> (str, str):
    """
    generates a unique session id (uuid4), signs it with itsdangerous.Signer
    and encodes with b64 encoder to use as a Cookie value
    """
    signer = get_signer()
    session_id = uuid4_string()
    signed = signer.sign(session_id)
    return session_id, b64encode(signed).decode()


def read_session_id(cookie_str: str) -> Optional[str]:
    signer = get_signer()

    try:
        signed = b64decode(cookie_str.encode())
    except Base64Error:
        return None

    try:
        session_id = signer.unsign(signed)
    except BadSignature:
        return None

    return session_id.decode()


class BaseSession(StorableModel):
    sid: str
    created_at: datetime = now
    updated_at: datetime = now

    __indexes__ = (
        ["sid", {"unique": True}],
    )

    __key_field__ = "sid"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.modified = False

    async def _before_save(self):
        if not self.is_new:
            self.touch()

    def touch(self):
        self.updated_at = now()


def create_session_middleware(session_class: Type[BaseSession]):
    cookie_name = ctx.cfg.get("session_cookie_name", "_uengine_sid")

    async def session_middleware(
            request: Request,
            call_next):
        session = None
        cookie_sid = request.cookies.get(cookie_name)

        if cookie_sid:
            session_id = read_session_id(cookie_sid)
            if session_id:
                session = await session_class.get(session_id)

        if not session:
            session_id, cookie_sid = generate_session_id()
            session = session_class(sid=session_id)

        request.state.session = session
        response = await call_next(request)
        if session.modified:
            await session.save()

        response.set_cookie(cookie_name, cookie_sid)
        return response

    return session_middleware


def acquire_session(request: Request) -> BaseSession:
    return getattr(request.state, "session", None)
