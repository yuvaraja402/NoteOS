from random import sample

from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import Note, utc_now
from app.schemas import NoteCreate, NoteRead, NoteUpdate

settings = get_settings()
app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def serialize(note: Note) -> NoteRead:
    return NoteRead(
        id=note.id,
        title=note.title,
        content=note.content,
        tags=[tag for tag in note.tags.split(",") if tag],
        color=note.color,
        is_pinned=note.is_pinned,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


def apply_note(note: Note, payload: NoteCreate | NoteUpdate) -> Note:
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        if field == "tags":
            setattr(note, field, ",".join(value))
        else:
            setattr(note, field, value)
    note.updated_at = utc_now()
    return note


@app.get("/health")
@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "noteos-api"}


@app.get("/notes", response_model=list[NoteRead])
@app.get("/api/notes", response_model=list[NoteRead])
def list_notes(db: Session = Depends(get_db)) -> list[NoteRead]:
    notes = db.scalars(select(Note).order_by(Note.updated_at.desc())).all()
    if notes:
        return [serialize(note) for note in notes]

    seed_pool = [
        Note(
            title="Shopping list",
            content="- coffee beans\n- oat milk\n- fresh fruit\n- dinner ingredients",
            tags="personal,errands",
            color="citrus",
        ),
        Note(
            title="Project strategy",
            content="Focus\n- Make the first workflow feel instant\n- Keep the interface calm\n- Review progress every Friday",
            tags="strategy,work",
            color="sea",
            is_pinned=True,
        ),
        Note(
            title="Roadmap ideas",
            content="Next\n- Better search\n- Shared note links\n- Weekly planning view",
            tags="roadmap,product",
            color="sky",
            is_pinned=True,
        ),
        Note(
            title="Reading queue",
            content="- Design systems notes\n- Product onboarding examples\n- Team operating cadence",
            tags="learning",
            color="coral",
        ),
        Note(
            title="Weekend plan",
            content="- Long walk\n- Clean desk\n- Prep meals\n- Call home",
            tags="personal",
            color="sea",
        ),
    ]
    seed = sample(seed_pool, k=3)
    db.add_all(seed)
    db.commit()
    return [serialize(note) for note in seed]


@app.post("/notes", response_model=NoteRead, status_code=status.HTTP_201_CREATED)
@app.post("/api/notes", response_model=NoteRead, status_code=status.HTTP_201_CREATED)
def create_note(payload: NoteCreate, db: Session = Depends(get_db)) -> NoteRead:
    note = apply_note(Note(), payload)
    db.add(note)
    db.commit()
    db.refresh(note)
    return serialize(note)


@app.patch("/notes/{note_id}", response_model=NoteRead)
@app.patch("/api/notes/{note_id}", response_model=NoteRead)
def update_note(note_id: str, payload: NoteUpdate, db: Session = Depends(get_db)) -> NoteRead:
    note = db.get(Note, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    apply_note(note, payload)
    db.commit()
    db.refresh(note)
    return serialize(note)


@app.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
@app.delete("/api/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_note(note_id: str, db: Session = Depends(get_db)) -> Response:
    note = db.get(Note, note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    db.delete(note)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
