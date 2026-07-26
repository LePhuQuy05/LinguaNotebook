"use client";

import { useOffline } from "../../hooks/useOffline";
import { Wifi, WifiOff } from "lucide-react";

export function NetworkStatus() {
  const { isOnline } = useOffline();

  if (isOnline) return null;

  return (
    <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-50 rounded-full bg-destructive px-4 py-2 text-sm font-medium text-white shadow-lg flex items-center gap-2 animate-slide-up">
      <WifiOff className="h-4 w-4" />
      You are offline — changes will sync when reconnected
    </div>
  );
}
