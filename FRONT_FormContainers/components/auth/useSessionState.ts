"use client";

import { useEffect, useState } from "react";
import {
  getAuthToken,
  AUTH_TOKEN_KEY,
  AUTH_USERNAME_KEY,
  AUTH_IS_STAFF_KEY,
} from "@/lib/api.admin";

type SessionSnapshot = {
  authed: boolean;
  username: string | null;
  isStaff: boolean;
  ready: boolean;
};

const DEFAULT_STATE: SessionSnapshot = {
  authed: false,
  username: null,
  isStaff: false,
  ready: false,
};

function parseBool(value: string | null | undefined) {
  if (!value) return false;
  const lowered = value.trim().toLowerCase();
  return lowered === "1" || lowered === "true" || lowered === "yes" || lowered === "on";
}

function readSnapshot(): SessionSnapshot {
  if (typeof window === "undefined") {
    return DEFAULT_STATE;
  }

  const token = getAuthToken();
  let username: string | null = null;
  let isStaff = false;

  try {
    username = localStorage.getItem(AUTH_USERNAME_KEY);
  } catch {
    username = null;
  }

  try {
    isStaff = parseBool(localStorage.getItem(AUTH_IS_STAFF_KEY));
  } catch {
    isStaff = false;
  }

  return {
    authed: Boolean(token),
    username: username && username.trim() ? username.trim() : null,
    isStaff,
    ready: true,
  };
}

export function useSessionState(): SessionSnapshot {
  const [snapshot, setSnapshot] = useState<SessionSnapshot>(() => readSnapshot());

  useEffect(() => {
    if (typeof window === "undefined") return;

    const recompute = () => {
      setSnapshot((prev) => {
        const next = readSnapshot();
        if (
          prev.authed === next.authed &&
          prev.username === next.username &&
          prev.isStaff === next.isStaff &&
          prev.ready === next.ready
        ) {
          return prev;
        }
        return next;
      });
    };

    const onAuthChanged = () => recompute();
    const onStorage = (event: StorageEvent) => {
      if (
        !event.key ||
        event.key === AUTH_TOKEN_KEY ||
        event.key === AUTH_USERNAME_KEY ||
        event.key === AUTH_IS_STAFF_KEY
      ) {
        recompute();
      }
    };
    const onFocus = () => recompute();
    const onVisibility = () => {
      if (document.visibilityState === "visible") recompute();
    };

    recompute();

    window.addEventListener("auth:changed", onAuthChanged as EventListener);
    window.addEventListener("storage", onStorage);
    window.addEventListener("focus", onFocus);
    document.addEventListener("visibilitychange", onVisibility);

    return () => {
      window.removeEventListener("auth:changed", onAuthChanged as EventListener);
      window.removeEventListener("storage", onStorage);
      window.removeEventListener("focus", onFocus);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, []);

  return snapshot;
}
