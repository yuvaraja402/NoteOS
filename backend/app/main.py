import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from uuid import UUID, uuid4

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from redis import Redis
from redis.exceptions import RedisError

from app.config import Settings, get_settings
from app.identity import COOKIE_MAX_AGE, COOKIE_NAME, device_identity, digest
from app.schemas import NoteBase, NoteCreate, NoteRead, NoteUpdate
from app.secrets import read_secret
from app.store import BusyWorkspace, NoteStore

logger = logging.getLogger(__name__)


async def flush_loop(store, interval):
    while True:
        try:
            await asyncio.to_thread(store.flush_due_workspaces)
        except Exception:
            logger.error("Cloud flush worker failed; pending writes remain queued")
        await asyncio.sleep(interval)


@asynccontextmanager
async def lifespan(app):
    settings = get_settings()
    auth_token = read_secret(settings.redis_auth_ssm_param, settings.aws_region)
    session_key = read_secret(settings.session_key_ssm_param, settings.aws_region)
    if len(session_key.encode()) < 32:
        raise RuntimeError("The session signing key must contain at least 32 bytes.")
    redis_client = Redis(
        host=settings.redis_host, port=settings.redis_port, password=auth_token,
        ssl=True, ssl_cert_reqs="required", decode_responses=True,
        socket_connect_timeout=5, socket_timeout=5,
    )
    redis_client.ping()
    table = boto3.resource(
        "dynamodb", region_name=settings.aws_region,
        config=Config(connect_timeout=5, read_timeout=5, retries={"max_attempts": 2}),
    ).Table(settings.table_name)
    table.load()
    app.state.settings = settings
    app.state.session_key = session_key
    app.state.store = NoteStore(redis_client, table, settings)
    worker = asyncio.create_task(flush_loop(app.state.store, settings.flush_poll_seconds))
    try:
        yield
    finally:
        worker.cancel()
        with suppress(asyncio.CancelledError):
            await worker
        redis_client.close()


app = FastAPI(title="NotesOS API", lifespan=lifespan)
# Reading origins does not require cloud access; resource validation happens at startup.
app.add_middleware(
    CORSMiddleware,
    allow_origins=Settings().cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def storage_errors(request, call_next):
    try:
        response = await call_next(request)
    except (RedisError, BotoCoreError, ClientError, BusyWorkspace):
        from fastapi.responses import JSONResponse
        response = JSONResponse(
            {"detail": "Cloud storage is temporarily unavailable. Keep your browser drafts."},
            status_code=503,
        )
    response.headers["Cache-Control"] = "no-store"
    return response


def workspace(request: Request, response: Response):
    settings = request.app.state.settings
    secret = request.app.state.session_key
    store = request.app.state.store
    # Only the trusted ALB can reach deployed tasks. ALB appends the actual client IP.
    address = request.client.host if request.client else "unknown"
    if settings.is_production_like:
        address = request.headers.get("x-forwarded-for", address).split(",")[-1].strip()
    ip_identity = digest(secret, "ip", address)
    if not store.rate_limit(ip_identity, 1200):
        raise HTTPException(429, "Too many requests. Try again shortly.")
    identity, token, new_cookie = device_identity(request.cookies.get(COOKIE_NAME), secret)
    if not store.rate_limit(identity, 240):
        raise HTTPException(429, "Too many requests. Try again shortly.")
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        origin = request.headers.get("origin")
        if origin and origin not in settings.cors_origins:
            raise HTTPException(403, "Origin is not allowed.")
    if new_cookie:
        response.set_cookie(
            COOKIE_NAME, token, httponly=True, secure=settings.is_production_like,
            samesite="lax", max_age=COOKIE_MAX_AGE, path="/",
        )
    return identity


def store(request: Request):
    return request.app.state.store


@app.get("/health")
@app.get("/api/health")
def health(request: Request):
    request.app.state.store.redis.ping()
    return {"status": "ok", "service": "noteos-api"}


@app.get("/workspace")
@app.get("/api/workspace")
def get_workspace(identity=Depends(workspace), repository=Depends(store)):
    document = repository.snapshot(identity)
    return {
        "workspace_id": identity,
        "notes": document["notes"],
        "status": "buffered" if document["dirty"] else "persisted",
        "flush_due_at": document["due_at"],
        "persisted_at": document["persisted_at"],
        "revision": document["revision"],
        "persisted_revision": document["persisted_revision"],
        "is_new": document["revision"] == 0,
    }


@app.get("/notes", response_model=list[NoteRead])
@app.get("/api/notes", response_model=list[NoteRead])
def list_notes(identity=Depends(workspace), repository=Depends(store)):
    return repository.snapshot(identity)["notes"]


def save(repository, identity, note_id, payload, response, patch=False):
    try:
        note, revision = repository.save_note(identity, str(note_id), payload, patch=patch)
        response.headers["X-NoteOS-Revision"] = str(revision)
        return note
    except KeyError:
        raise HTTPException(404, "Note not found") from None
    except ValueError as error:
        raise HTTPException(413, str(error)) from None


@app.post("/notes", response_model=NoteRead, status_code=201)
@app.post("/api/notes", response_model=NoteRead, status_code=201)
def create_note(payload: NoteCreate, response: Response, identity=Depends(workspace), repository=Depends(store)):
    return save(repository, identity, uuid4(), payload.model_dump(), response)


@app.put("/notes/{note_id}", response_model=NoteRead)
@app.put("/api/notes/{note_id}", response_model=NoteRead)
def put_note(note_id: UUID, payload: NoteBase, response: Response, identity=Depends(workspace), repository=Depends(store)):
    # Client-generated UUIDs make replaying the browser outbox idempotent.
    return save(repository, identity, note_id, payload.model_dump(), response)


@app.patch("/notes/{note_id}", response_model=NoteRead)
@app.patch("/api/notes/{note_id}", response_model=NoteRead)
def update_note(note_id: UUID, payload: NoteUpdate, response: Response, identity=Depends(workspace), repository=Depends(store)):
    return save(repository, identity, note_id, payload.model_dump(exclude_unset=True, exclude_none=True), response, patch=True)


@app.delete("/notes/{note_id}", status_code=204)
@app.delete("/api/notes/{note_id}", status_code=204)
def delete_note(note_id: UUID, response: Response, identity=Depends(workspace), repository=Depends(store)):
    _, revision = repository.delete_note(identity, str(note_id))
    response.headers["X-NoteOS-Revision"] = str(revision)
    response.status_code = 204
    return response
