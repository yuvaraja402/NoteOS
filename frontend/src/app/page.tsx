"use client";

import {
  Check,
  Clock3,
  Cloud,
  FilePenLine,
  Loader2,
  Palette,
  Plus,
  Search,
  Sparkles,
  Tags,
  Trash2,
} from "lucide-react";
import { useEffect, useMemo, useState, useTransition } from "react";

type Note = {
  id: string;
  title: string;
  content: string;
  tags: string[];
  color: string;
  is_pinned: boolean;
  created_at: string;
  updated_at: string;
};

const starterNote = {
  title: "Quick capture",
  content: "Write the first version here. You can tag it, color it, and refine it later.",
  tags: ["idea"],
  color: "sea",
  is_pinned: false,
};

const colorOptions = [
  { value: "sea", label: "Sea" },
  { value: "sky", label: "Sky" },
  { value: "coral", label: "Coral" },
  { value: "citrus", label: "Citrus" },
];

function parseTags(value: string) {
  return value
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    throw new Error(`API request failed with ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

export default function Home() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [activeId, setActiveId] = useState("");
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("Connecting to NotesOS API");
  const [error, setError] = useState("");
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    let alive = true;

    request<Note[]>("/notes")
      .then((items) => {
        if (!alive) return;
        setNotes(items);
        setActiveId(items[0]?.id ?? "");
        setStatus("Data synced");
      })
      .catch(() => {
        if (!alive) return;
        setError("Start the API on port 8000 to enable live CRUD.");
        setStatus("Offline");
      });

    return () => {
      alive = false;
    };
  }, []);

  const filteredNotes = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const ordered = [...notes].sort((a, b) => {
      if (a.is_pinned !== b.is_pinned) return a.is_pinned ? -1 : 1;
      return +new Date(b.updated_at) - +new Date(a.updated_at);
    });

    if (!needle) return ordered;

    return ordered.filter((note) =>
      [note.title, note.content, note.tags.join(" ")]
        .join(" ")
        .toLowerCase()
        .includes(needle),
    );
  }, [notes, query]);

  const activeNote =
    notes.find((note) => note.id === activeId) ?? filteredNotes[0] ?? null;

  function replaceNote(nextNote: Note) {
    setNotes((current) =>
      current.map((note) => (note.id === nextNote.id ? nextNote : note)),
    );
  }

  function createNote() {
    startTransition(async () => {
      try {
        const created = await request<Note>("/notes", {
          method: "POST",
          body: JSON.stringify(starterNote),
        });
        setNotes((current) => [created, ...current]);
        setActiveId(created.id);
        setStatus("New note created");
        setError("");
      } catch {
        setError("Could not create the note. Check the API logs.");
      }
    });
  }

  function updateNote(patch: Partial<Note>) {
    if (!activeNote) return;
    const optimistic = {
      ...activeNote,
      ...patch,
      updated_at: new Date().toISOString(),
    };
    replaceNote(optimistic);
    setStatus("Saving");

    startTransition(async () => {
      try {
        const saved = await request<Note>(`/notes/${activeNote.id}`, {
          method: "PATCH",
          body: JSON.stringify(patch),
        });
        replaceNote(saved);
        setStatus("Saved");
        setError("");
      } catch {
        setError("Save failed. The local view kept your latest edit.");
        setStatus("Needs retry");
      }
    });
  }

  function deleteNote() {
    if (!activeNote) return;

    startTransition(async () => {
      try {
        await request<void>(`/notes/${activeNote.id}`, { method: "DELETE" });
        setNotes((current) =>
          current.filter((note) => note.id !== activeNote.id),
        );
        setActiveId(
          filteredNotes.find((note) => note.id !== activeNote.id)?.id ?? "",
        );
        setStatus("Note deleted");
      } catch {
        setError("Delete failed. Check the API logs.");
      }
    });
  }

  return (
    <main className="workspace">
      <section className="topbar" aria-label="NotesOS status bar">
        <div>
          <p className="eyebrow">NotesOS</p>
          <h1>Write, sort, ship your thoughts.</h1>
        </div>
        <div className="topbar-actions">
          <span className="sync-pill">
            {isPending ? (
              <Loader2 className="spin" size={16} />
            ) : (
              <Cloud size={16} />
            )}
            {status}
          </span>
          <button className="primary-action" onClick={createNote}>
            <Plus size={18} />
            New note
          </button>
        </div>
      </section>

      <section className="glass-frame" aria-label="Notes workspace">
        <aside className="sidebar">
          <div className="search-box">
            <Search size={17} />
            <input
              aria-label="Search notes"
              placeholder="Search notes, tags, ideas"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
          </div>

          <div className="note-list">
            {filteredNotes.map((note) => (
              <button
                className={`note-row ${
                  note.id === activeNote?.id ? "active" : ""
                }`}
                key={note.id}
                onClick={() => setActiveId(note.id)}
              >
                <span className={`note-swatch ${note.color}`} />
                <span>
                  <strong>{note.title || "Untitled note"}</strong>
                  <small>{note.content || "No content yet"}</small>
                </span>
                {note.is_pinned && <Sparkles size={15} />}
              </button>
            ))}
          </div>
        </aside>

        <article className="editor">
          {activeNote ? (
            <>
              <div className="editor-head">
                <div>
                  <span className="section-label">
                    <FilePenLine size={15} />
                    Current note
                  </span>
                  <input
                    className="title-input"
                    aria-label="Note title"
                    value={activeNote.title}
                    onChange={(event) =>
                      updateNote({ title: event.target.value })
                    }
                  />
                </div>
                <div className="editor-tools">
                  <button
                    className={activeNote.is_pinned ? "tool on" : "tool"}
                    onClick={() =>
                      updateNote({ is_pinned: !activeNote.is_pinned })
                    }
                    title="Pin note"
                  >
                    <Sparkles size={17} />
                  </button>
                  <button
                    className="tool danger"
                    onClick={deleteNote}
                    title="Delete note"
                  >
                    <Trash2 size={17} />
                  </button>
                </div>
              </div>

              <div className="note-controls" aria-label="Note tagging controls">
                <label className="tag-field">
                  <span>
                    <Tags size={15} />
                    Tags
                  </span>
                  <input
                    aria-label="Note tags"
                    placeholder="shopping, roadmap, strategy"
                    value={activeNote.tags.join(", ")}
                    onChange={(event) =>
                      updateNote({ tags: parseTags(event.target.value) })
                    }
                  />
                </label>

                <div className="color-field">
                  <span>
                    <Palette size={15} />
                    Color
                  </span>
                  <div className="color-options">
                    {colorOptions.map((option) => (
                      <button
                        key={option.value}
                        className={`color-dot ${option.value} ${
                          activeNote.color === option.value ? "selected" : ""
                        }`}
                        onClick={() => updateNote({ color: option.value })}
                        title={`${option.label} note color`}
                        aria-label={`${option.label} note color`}
                      />
                    ))}
                  </div>
                </div>
              </div>

              <textarea
                className="content-input"
                aria-label="Note content"
                value={activeNote.content}
                onChange={(event) => updateNote({ content: event.target.value })}
              />

              <div className="metadata-strip">
                <span>
                  <Clock3 size={15} />
                  Updated {formatDate(activeNote.updated_at)}
                </span>
                <span>
                  <Check size={15} />
                  Data sync status: {status}
                </span>
              </div>
            </>
          ) : (
            <div className="empty-state">
              <Sparkles size={26} />
              <h2>No notes yet</h2>
              <p>Create the first note once the API is running.</p>
              <button className="primary-action" onClick={createNote}>
                <Plus size={18} />
                New note
              </button>
            </div>
          )}
        </article>
      </section>

      {error && <p className="error-banner">{error}</p>}
    </main>
  );
}
