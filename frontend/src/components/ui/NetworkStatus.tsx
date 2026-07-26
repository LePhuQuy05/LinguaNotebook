"use client";

import { useState, useEffect } from "react";
import { WifiOff } from "lucide-react";

export function NetworkStatus() {
  const [showOffline, setShowOffline] = useState(false);

  useEffect(() => {
    // Only show after a confirmed disconnect event, never on initial load
    const handleOffline = () => setShowOffline(true);
    const handleOnline = () => setShowOffline(false);

    // Don't check on mount — only react to changes
    window.addEventListener("offline", handleOffline);
    window.addEventListener("online", handleOnline);
    return () => {
      window.removeEventListener("offline", handleOffline);
      window.removeEventListener("online", handleOnline);
    };
  }, []);

  if (!showOffline) return null;

  return (
    <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50 rounded-full bg-destructive px-4 py-2 text-sm font-medium text-white shadow-lg flex items-center gap-2">
      <WifiOff className="h-4 w-4" />
      You are offline — changes will sync when reconnected
    </div>
  );
}
