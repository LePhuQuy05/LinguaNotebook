// IndexedDB offline storage using Dexie.js
import Dexie, { type EntityTable } from "dexie";

interface OfflineDocument {
  id: string;
  filename: string;
  cachedAt: number;
}

interface OfflineLesson {
  id: string;
  data: string; // JSON stringified
  cachedAt: number;
}

interface PendingChange {
  id?: number;
  entityType: string;
  entityId: string;
  action: "created" | "updated" | "deleted";
  payload: string;
  clientTimestamp: string;
  synced: boolean;
}

const db = new Dexie("LinguaNotebookOffline") as Dexie & {
  documents: EntityTable<OfflineDocument, "id">;
  lessons: EntityTable<OfflineLesson, "id">;
  pendingChanges: EntityTable<PendingChange, "id">;
};

db.version(1).stores({
  documents: "id, cachedAt",
  lessons: "id, cachedAt",
  pendingChanges: "++id, entityType, synced",
});

export async function cacheDocument(doc: OfflineDocument): Promise<void> {
  await db.documents.put(doc);
}

export async function getCachedDocument(id: string): Promise<OfflineDocument | undefined> {
  return db.documents.get(id);
}

export async function cacheLesson(id: string, data: unknown): Promise<void> {
  await db.lessons.put({ id, data: JSON.stringify(data), cachedAt: Date.now() });
}

export async function getCachedLesson(id: string): Promise<unknown | undefined> {
  const entry = await db.lessons.get(id);
  return entry ? JSON.parse(entry.data) : undefined;
}

export async function queueChange(
  entityType: string,
  entityId: string,
  action: "created" | "updated" | "deleted",
  payload: unknown,
): Promise<void> {
  await db.pendingChanges.add({
    entityType,
    entityId,
    action,
    payload: JSON.stringify(payload),
    clientTimestamp: new Date().toISOString(),
    synced: false,
  });
}

export async function getPendingChanges(): Promise<PendingChange[]> {
  // `synced` is indexed as a boolean, which Dexie's `equals()` typing
  // rejects — filter in memory instead (queue is small).
  return db.pendingChanges.filter((c) => !c.synced).toArray();
}

export async function markSynced(ids: number[]): Promise<void> {
  await db.pendingChanges.where("id").anyOf(ids).modify({ synced: true });
}

export { db };
