"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { getPendingChanges, markSynced, queueChange } from "../lib/offline-db";

export function useOffline() {
  const [isOnline, setIsOnline] = useState(
    typeof navigator !== "undefined" ? navigator.onLine : true,
  );
  const syncInProgress = useRef(false);

  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      syncPendingChanges();
    };
    const handleOffline = () => setIsOnline(false);

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  const syncPendingChanges = useCallback(async () => {
    if (syncInProgress.current) return;
    syncInProgress.current = true;

    try {
      const pending = await getPendingChanges();
      if (pending.length === 0) return;

      const token = localStorage.getItem("token");
      const res = await fetch("/api/v1/sync/push", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          device_id: localStorage.getItem("device_id") || "web",
          changes: pending.map((c) => ({
            entity_type: c.entityType,
            entity_id: c.entityId,
            action: c.action,
            client_timestamp: c.clientTimestamp,
            payload_hash: c.payload,
          })),
        }),
      });

      if (res.ok) {
        const syncedIds = pending.map((c) => c.id).filter(Boolean) as number[];
        await markSynced(syncedIds);
      }
    } catch (e) {
      // Will retry on next online event
    } finally {
      syncInProgress.current = false;
    }
  }, []);

  // Pull changes from server
  const pullChanges = useCallback(async () => {
    const token = localStorage.getItem("token");
    const lastSync = localStorage.getItem("last_sync") || new Date(0).toISOString();
    const res = await fetch(
      `/api/v1/sync/pull?since=${encodeURIComponent(lastSync)}`,
      { headers: { Authorization: `Bearer ${token}` } },
    );
    if (res.ok) {
      const data = await res.json();
      localStorage.setItem("last_sync", data.server_time);
      return data.changes;
    }
    return [];
  }, []);

  return { isOnline, syncPendingChanges, pullChanges, queueChange };
}
