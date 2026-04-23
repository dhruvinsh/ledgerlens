import { useEffect, type RefObject } from "react";
import { useLocation } from "react-router";

const KEY_PREFIX = "ll-scroll:";
const INDEX_KEY = "ll-scroll-index";
const SESSION_ID_KEY = "ll-session-id";
// Cap so sessionStorage can't grow unbounded as location.key changes on every
// navigation (including each replace-based filter tweak).
const MAX_ENTRIES = 50;

let indexCache: string[] | null = null;
let sessionIdCache: string | null = null;

function loadIndex(): string[] {
  if (indexCache) return indexCache;
  try {
    const raw = sessionStorage.getItem(INDEX_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    indexCache = Array.isArray(parsed) ? parsed : [];
  } catch {
    indexCache = [];
  }
  return indexCache;
}

// react-router assigns location.key === "default" to the first entry of a
// session. Two separate bookmark visits landing on the same URL would collide
// under that shared key, so substitute a per-tab UUID when we see "default".
function getSessionId(): string {
  if (sessionIdCache) return sessionIdCache;
  try {
    const existing = sessionStorage.getItem(SESSION_ID_KEY);
    if (existing) {
      sessionIdCache = existing;
      return existing;
    }
  } catch { /* ignore */ }
  const fresh =
    typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
      ? crypto.randomUUID()
      : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  sessionIdCache = fresh;
  try { sessionStorage.setItem(SESSION_ID_KEY, fresh); } catch { /* ignore */ }
  return fresh;
}

function resolveKey(loc: { key: string; pathname: string; search: string }): string {
  const base = loc.key && loc.key !== "default" ? loc.key : `default-${getSessionId()}`;
  return `${KEY_PREFIX}${base}:${loc.pathname}${loc.search}`;
}

function saveScroll(key: string, value: string) {
  const idx = loadIndex();
  const pos = idx.indexOf(key);
  if (pos !== -1) idx.splice(pos, 1);
  idx.push(key);
  while (idx.length > MAX_ENTRIES) {
    const oldest = idx.shift();
    if (oldest !== undefined) {
      try { sessionStorage.removeItem(oldest); } catch { /* ignore */ }
    }
  }
  try {
    sessionStorage.setItem(key, value);
    sessionStorage.setItem(INDEX_KEY, JSON.stringify(idx));
  } catch {
    // Quota still exceeded (other origins, foreign entries, huge index) —
    // drop oldest and retry once, then give up.
    if (idx.length > 1) {
      const oldest = idx.shift();
      if (oldest !== undefined) {
        try { sessionStorage.removeItem(oldest); } catch { /* ignore */ }
      }
      try {
        sessionStorage.setItem(key, value);
        sessionStorage.setItem(INDEX_KEY, JSON.stringify(idx));
      } catch { /* best-effort — drop this write */ }
    }
  }
}

// Restores the scroll position of a scroll container (e.g. AppShell's <main>)
// across back/forward navigation, including mobile edge-swipe. Keyed by
// location.key + pathname + search so POP restores, replace-based filter
// changes scroll to top, and fresh pushes start at top.
export function useScrollRestoration(ref: RefObject<HTMLElement | null>) {
  const location = useLocation();
  const storageKey = resolveKey(location);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const saved = sessionStorage.getItem(storageKey);
    const target = saved !== null ? Number(saved) : 0;

    // Programmatic scrolls fire a scroll event — suppress the save for one
    // frame so our own restore writes don't clobber the saved target before
    // async content has finished laying out.
    let suppress = 0;
    const setScroll = (v: number) => {
      suppress++;
      el.scrollTop = v;
      requestAnimationFrame(() => {
        suppress--;
      });
    };

    setScroll(target);

    // Async data (React Query) arrives after mount, so retry until scrollHeight
    // accommodates the target or a 2-second grace period ends. Also bail early
    // if scrollHeight stays stable for ~150ms and still can't fit the target —
    // the list is genuinely shorter now (e.g. after a delete), so no point
    // re-smashing scrollTop against the clamp for the full window.
    let retry: number | undefined;
    if (target > 0) {
      let tries = 0;
      let prevHeight = el.scrollHeight;
      let stableTicks = 0;
      retry = window.setInterval(() => {
        if (el.scrollHeight === prevHeight) {
          stableTicks++;
        } else {
          stableTicks = 0;
          prevHeight = el.scrollHeight;
        }
        const maxScroll = el.scrollHeight - el.clientHeight;
        const stableAndClamped = stableTicks >= 3 && maxScroll < target;
        if (++tries > 40 || el.scrollTop >= target || stableAndClamped) {
          clearInterval(retry);
          return;
        }
        setScroll(target);
      }, 50);
    }

    let rafId: number | null = null;
    const onScroll = () => {
      if (suppress > 0 || rafId !== null) return;
      rafId = requestAnimationFrame(() => {
        saveScroll(storageKey, String(el.scrollTop));
        rafId = null;
      });
    };
    el.addEventListener("scroll", onScroll, { passive: true });

    return () => {
      el.removeEventListener("scroll", onScroll);
      if (rafId !== null) cancelAnimationFrame(rafId);
      if (retry !== undefined) clearInterval(retry);
    };
  }, [storageKey, ref]);
}
