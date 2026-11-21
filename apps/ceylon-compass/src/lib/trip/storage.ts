import type { Trip } from "./types";

const TRIPS_KEY = "cch:trips:v1";
const DRAFT_KEY = "cch:draft:v1";
const ACCOUNT_KEY = "cch:demo-account:v1";

export type DemoAccount = { name: string; email: string; createdAt: string; demo: true };

const hasStorage = () => typeof window !== "undefined" && !!window.localStorage;

function read<T>(key: string, fallback: T): T {
  if (!hasStorage()) return fallback;
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}
function write(key: string, value: unknown) {
  if (!hasStorage()) return;
  window.localStorage.setItem(key, JSON.stringify(value));
  window.dispatchEvent(new CustomEvent("cch:storage", { detail: key }));
}

export const listTrips = (): Trip[] =>
  read<Trip[]>(TRIPS_KEY, []).sort((a, b) => (b.updatedAt > a.updatedAt ? 1 : -1));
export const getTrip = (id: string) => listTrips().find((t) => t.id === id) ?? null;

export function saveTrip(trip: Trip): Trip {
  const saved = { ...trip, savedAt: trip.savedAt ?? new Date().toISOString(), updatedAt: new Date().toISOString() };
  const others = read<Trip[]>(TRIPS_KEY, []).filter((t) => t.id !== trip.id);
  write(TRIPS_KEY, [saved, ...others]);
  return saved;
}
export function deleteTrip(id: string) {
  write(TRIPS_KEY, read<Trip[]>(TRIPS_KEY, []).filter((t) => t.id !== id));
}
export const isSaved = (id: string) => read<Trip[]>(TRIPS_KEY, []).some((t) => t.id === id);

export const getDraft = () => read<Trip | null>(DRAFT_KEY, null);
export const setDraft = (trip: Trip) => write(DRAFT_KEY, trip);
export const clearDraft = () => hasStorage() && window.localStorage.removeItem(DRAFT_KEY);

export const getAccount = () => read<DemoAccount | null>(ACCOUNT_KEY, null);
export function signInDemo(name: string, email: string): DemoAccount {
  const acc: DemoAccount = { name, email, createdAt: new Date().toISOString(), demo: true };
  write(ACCOUNT_KEY, acc);
  return acc;
}
export function signOutDemo() {
  if (!hasStorage()) return;
  window.localStorage.removeItem(ACCOUNT_KEY);
  window.dispatchEvent(new CustomEvent("cch:storage", { detail: ACCOUNT_KEY }));
}
