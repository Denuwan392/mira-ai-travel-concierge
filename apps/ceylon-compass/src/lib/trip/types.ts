import type { PhotoKey } from "@/lib/photos";

export type Interest =
  | "nature"
  | "trains"
  | "beaches"
  | "wildlife"
  | "culture"
  | "food"
  | "tea"
  | "wellness"
  | "adventure";

export type Pace = "relaxed" | "balanced" | "active";

export type StopId = "sigiriya" | "kandy" | "nuwara" | "ella" | "yala" | "mirissa" | "galle";

export type Citation = { label: string; source: string; note?: string };

export type Message = {
  id: string;
  role: "user" | "mira";
  text: string;
  createdAt: string;
  changes?: string[];
  citations?: Citation[];
  suggestions?: string[];
};

/** The single shared trip object every planning surface reads and writes. */
export type Trip = {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  days: number;
  startDate: string | null; // ISO yyyy-mm-dd
  travelMonth: string | null; // e.g. "March" when only a month is known
  party: { adults: number; children: number };
  interests: Interest[];
  pace: Pace;
  style: string | null;
  requiredStops: StopId[];
  excludedStops: StopId[];
  stopExtras: Partial<Record<StopId, number>>;
  hotelChoices: Partial<Record<StopId, string>>;
  messages: Message[];
  briefCount: number; // how many briefs/follow-ups have been applied
  enquiry: Enquiry | null;
  savedAt: string | null;
};

export type Enquiry = {
  name: string;
  email: string;
  phone: string;
  notes: string;
  submittedAt: string;
  reference: string;
  demo: true;
};

export type Activity = {
  id: string;
  title: string;
  interests: Interest[];
  duration: string;
  photo: PhotoKey;
  blurb: string;
};

export type Hotel = {
  id: string;
  name: string;
  kind: string;
  photo: PhotoKey;
  blurb: string;
};

export type Stop = {
  id: StopId;
  name: string;
  region: string;
  lat: number;
  lon: number;
  photo: PhotoKey;
  headline: string;
  scores: Partial<Record<Interest, number>>;
  activities: Activity[];
  hotels: Hotel[];
};

export type ItineraryDay = {
  day: number;
  date: string | null;
  stopId: StopId;
  title: string;
  story: string;
  photo: PhotoKey;
  transfer: { from: string; to: string; mode: "train" | "drive"; hours: number } | null;
  activities: Activity[];
  isDeparture: boolean;
};

export type RouteStop = { stop: Stop; days: number; nights: number; hotel: Hotel };

export type Itinerary = {
  route: RouteStop[];
  days: ItineraryDay[];
  totalDays: number;
  totalNights: number;
};
