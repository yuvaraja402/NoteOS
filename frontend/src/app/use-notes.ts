"use client";

import { useEffect, useRef, useState } from "react";

export type Note = {
  id: string;
  title: string;
  content: string;
  tags: string[];
  color: string;
  is_pinned: boolean;
  created_at: string;
  updated_at: string;
};

type Mutation = { type: "put"; note: Note } | { type: "delete"; id: string };
type Workspace = { workspace_id: string; notes: Note[]; status: "buffered" | "persisted"; revision: number; persisted_revision: number; is_new: boolean };
type Buffered = { mutation: Mutation; revision: number };
type View = { notes: Note[]; status: string; error: string; isPending: boolean };
const SESSION_KEY = "noteos.session.v2";
const initial: View = { notes: [], status: "Opening your workspace", error: "", isPending: false };

function note(title: string, content: string, tags: string[], color: string): Note {
  const now = new Date().toISOString();
  return { id: crypto.randomUUID(), title, content, tags, color, is_pinned: false, created_at: now, updated_at: now };
}

async function request<T>(path: string, init?: RequestInit): Promise<{ data: T; revision: number }> {
  const response = await fetch(`/api${path}`, {
    ...init,
    credentials: "same-origin",
    cache: "no-store",
    headers: { "Content-Type": "application/json" },
    signal: AbortSignal.timeout(10000),
  });
  if (!response.ok) {
    if (response.status === 413) throw new Error("Workspace limit reached. Shorten or remove a note to sync.");
    if (response.status === 429) throw new Error("Sync is paused briefly. Your drafts are kept in this tab.");
    throw new Error("Cloud sync is unavailable. Your drafts are kept in this tab.");
  }
  return {
    data: response.status === 204 ? undefined as T : await response.json(),
    revision: Number(response.headers.get("X-NoteOS-Revision") ?? 0),
  };
}

class BrowserSession {
  notes: Note[] = [];
  pending: Record<string, Mutation> = {};
  buffered: Record<string, Buffered> = {};
  workspace = "";
  online = false;
  syncing = false;
  stopped = false;
  error = "";
  sessionSaved = true;
  cloudStatus = "persisted";
  canSeed = true;
  firstSendAt = 0;
  timer?: ReturnType<typeof setTimeout>;
  poll?: ReturnType<typeof setInterval>;

  constructor(private emit: (view: View) => void) {}

  notify() {
    if (this.stopped) return;
    const status = !this.sessionSaved ? "Kept in memory; keep tab open" : !this.online ? "Saved in this tab" : Object.keys(this.pending).length
      ? "Saved in this tab; syncing" : this.cloudStatus === "buffered" || Object.keys(this.buffered).length ? "Buffered in cloud" : "Saved to cloud";
    this.emit({ notes: [...this.notes], status, error: this.error, isPending: this.syncing });
  }

  persist() {
    if (this.stopped) return;
    try {
      sessionStorage.setItem(SESSION_KEY, JSON.stringify({ notes: this.notes, pending: this.pending, buffered: this.buffered, workspace: this.workspace }));
      this.sessionSaved = true;
    } catch {
      this.sessionSaved = false;
      this.error = "Browser storage is unavailable or full. Keep this tab open until cloud sync completes.";
    }
  }

  seed() {
    const candidates = [
      ["Shopping list", "- Coffee beans\n- Fresh fruit\n- Dinner ingredients", "personal", "citrus"],
      ["Project strategy", "Focus\n- Make the first workflow feel instant\n- Review progress every Friday", "work", "sea"],
      ["Roadmap ideas", "Next\n- Better search\n- Shared note links\n- Weekly planning", "ideas", "sky"],
      ["Weekend plan", "- Long walk\n- Meal prep\n- Call home", "personal", "coral"],
      ["Reading queue", "- Design systems\n- Product onboarding\n- Team habits", "learning", "sea"],
    ];
    for (let index = candidates.length - 1; index > 0; index--) {
      const random = Math.floor(Math.random() * (index + 1));
      [candidates[index], candidates[random]] = [candidates[random], candidates[index]];
    }
    this.notes = candidates.slice(0, 3).map(([title, content, tag, color]) => note(title, content, [tag], color));
    for (const item of this.notes) this.pending[item.id] = { type: "put", note: item };
  }

  async start() {
    await Promise.resolve();
    if (this.stopped) return;
    let restored = false;
    try {
      const cached = JSON.parse(sessionStorage.getItem(SESSION_KEY) ?? "null");
      if (cached && Array.isArray(cached.notes) && cached.pending && typeof cached.workspace === "string") {
        this.notes = cached.notes;
        this.pending = cached.pending;
        this.buffered = cached.buffered ?? {};
        this.workspace = cached.workspace;
        restored = true;
      }
    } catch { /* An unreadable cache starts a fresh browser session. */ }
    this.notify();
    await this.connect();
    if (this.stopped) return;
    if (!restored && this.notes.length === 0 && this.canSeed) this.seed();
    this.persist();
    this.notify();
    this.schedule();
    this.poll = setInterval(() => {
      if (this.syncing || this.stopped) return;
      void (this.online && Object.keys(this.pending).length ? this.flush() : this.connect());
    }, 5000);
  }

  async connect() {
    if (this.syncing || this.stopped) return;
    this.syncing = true;
    try {
      const { data: remote } = await request<Workspace>("/workspace");
      if (this.stopped) return;
      if (this.workspace && this.workspace !== remote.workspace_id) {
        // Cookie changes must not replay an old device's drafts into a new workspace.
        this.pending = {};
        this.buffered = {};
        this.error = "A new device session was opened.";
      } else this.error = "";
      this.workspace = remote.workspace_id;
      this.canSeed = remote.is_new;
      for (const [id, buffered] of Object.entries(this.buffered)) {
        if (remote.persisted_revision >= buffered.revision) delete this.buffered[id];
        else if (remote.revision < buffered.revision && !this.pending[id]) {
          this.pending[id] = buffered.mutation;
        }
      }
      const merged = new Map(remote.notes.map((item) => [item.id, item]));
      for (const [id, buffered] of Object.entries(this.buffered)) {
        if (buffered.mutation.type === "delete") merged.delete(id);
        else merged.set(id, buffered.mutation.note);
      }
      for (const [id, change] of Object.entries(this.pending)) {
        if (change.type === "delete") merged.delete(id);
        else merged.set(id, change.note);
      }
      this.notes = [...merged.values()];
      this.cloudStatus = remote.status;
      this.online = true;
      this.persist();
    } catch {
      this.online = false;
      this.error = "Cloud sync is unavailable. Keep this tab open to preserve drafts.";
    } finally {
      this.syncing = false;
      this.notify();
      if (this.online && Object.keys(this.pending).length) this.schedule();
    }
  }

  schedule() {
    if (this.stopped || !Object.keys(this.pending).length) return;
    if (!this.firstSendAt) this.firstSendAt = Date.now();
    clearTimeout(this.timer);
    const delay = Math.min(750, Math.max(0, this.firstSendAt + 2000 - Date.now()));
    this.timer = setTimeout(() => { void this.flush(); }, delay);
  }

  enqueue(id: string, mutation: Mutation) {
    this.pending[id] = mutation;
    this.persist();
    this.notify();
    this.schedule();
  }

  async flush() {
    if (!this.online || this.syncing || this.stopped) return;
    this.syncing = true;
    this.notify();
    try {
      const changes = Object.entries(this.pending).sort(([, a], [, b]) => Number(b.type === "delete") - Number(a.type === "delete"));
      for (const [id, mutation] of changes) {
        if (this.stopped) return;
        let revision: number;
        if (mutation.type === "delete") {
          const acknowledgement = await request<void>(`/notes/${id}`, { method: "DELETE" });
          revision = acknowledgement.revision;
        }
        else {
          const item = mutation.note;
          const acknowledgement = await request<Note>(`/notes/${id}`, {
            method: "PUT",
            body: JSON.stringify({ title: item.title || "Untitled note", content: item.content, tags: item.tags, color: item.color, is_pinned: item.is_pinned }),
          });
          revision = acknowledgement.revision;
        }
        if (!revision) throw new Error("Cloud sync did not confirm this revision. Your drafts are kept in this tab.");
        this.buffered[id] = { mutation, revision };
        // A newer edit made during this request must stay in the outbox.
        if (this.pending[id] === mutation) delete this.pending[id];
        this.cloudStatus = "buffered";
        this.persist();
      }
      this.error = "";
    } catch (error) {
      this.online = false;
      this.error = error instanceof Error ? error.message : "Your changes are kept in this tab.";
    } finally {
      this.firstSendAt = 0;
      this.syncing = false;
      this.notify();
      if (this.online && Object.keys(this.pending).length) this.schedule();
    }
  }

  create() {
    const item = note("Quick capture", "", ["idea"], "sea");
    this.notes = [item, ...this.notes];
    this.enqueue(item.id, { type: "put", note: item });
    return item.id;
  }

  update(id: string, patch: Partial<Note>) {
    const current = this.notes.find((item) => item.id === id);
    if (!current) return;
    const changed = { ...current, ...patch, updated_at: new Date().toISOString() };
    this.notes = this.notes.map((item) => item.id === id ? changed : item);
    this.enqueue(id, { type: "put", note: changed });
  }

  remove(id: string) {
    this.notes = this.notes.filter((item) => item.id !== id);
    this.enqueue(id, { type: "delete", id });
  }

  stop() {
    this.stopped = true;
    clearTimeout(this.timer);
    clearInterval(this.poll);
  }
}

export function useNotes() {
  const [view, setView] = useState<View>(initial);
  const session = useRef<BrowserSession | null>(null);
  useEffect(() => {
    const controller = new BrowserSession(setView);
    session.current = controller;
    void controller.start();
    return () => controller.stop();
  }, []);
  return {
    ...view,
    createNote: () => session.current?.create() ?? "",
    updateNote: (id: string, patch: Partial<Note>) => session.current?.update(id, patch),
    deleteNote: (id: string) => session.current?.remove(id),
  };
}
