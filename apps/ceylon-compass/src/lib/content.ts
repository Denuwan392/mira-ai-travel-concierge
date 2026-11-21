import type { PhotoKey } from "@/lib/photos";

export const STARTERS = [
  { label: "Family Adventure", brief: "Family adventure for 2 adults and 2 kids, 10 days, wildlife and beaches, relaxed pace" },
  { label: "Romantic Escape", brief: "Romantic escape for two, 8 days, tea country, a slow train and a quiet beach villa" },
  { label: "Wildlife", brief: "9 days focused on wildlife: leopards in Yala, elephants and whales" },
  { label: "Culture", brief: "7 days of culture: ancient temples, Sigiriya, Kandy and Galle Fort, with food" },
  { label: "Beaches", brief: "6 days of beaches on the south coast with a little culture in Galle, relaxed pace" },
  { label: "Surprise Me", brief: "Surprise me: 8 days for 2 adults" },
] as const;

export const DEMO_BRIEF = "We have 6 days and want nature, trains and beaches";
export const DEMO_FOLLOW_UP = "Add a day in Ella";

export type HeroSlide = {
  id: string;
  index: string;
  name: string;
  region: string;
  caption: string;
  coords: string;
  season: string;
  photo: PhotoKey;
  accent: "saffron" | "saffron-wash" | "maroon-wash";
};

export const HERO_SLIDES: HeroSlide[] = [
  { id: "sigiriya", index: "01", name: "Sigiriya", region: "Cultural Triangle", caption: "Lion Rock at first light", coords: "7.95° N · 80.76° E", season: "Best Jan – Apr", photo: "sigiriya", accent: "saffron" },
  { id: "ella", index: "02", name: "Ella", region: "Uva highlands", caption: "The morning train over Nine Arches", coords: "6.87° N · 81.05° E", season: "Best Jan – May", photo: "ella", accent: "saffron-wash" },
  { id: "galle", index: "03", name: "Galle", region: "Southern fort city", caption: "Ramparts at golden hour", coords: "6.03° N · 80.22° E", season: "Best Dec – Apr", photo: "galle", accent: "saffron" },
  { id: "yala", index: "04", name: "Yala", region: "Southern dry zone", caption: "A leopard on warm granite", coords: "6.37° N · 81.52° E", season: "Best Feb – Jul", photo: "yala", accent: "maroon-wash" },
  { id: "mirissa", index: "05", name: "Mirissa", region: "South coast", caption: "Blue whales beyond the shelf", coords: "5.95° N · 80.46° E", season: "Best Dec – Apr", photo: "mirissa", accent: "saffron-wash" },
];

export const STRIP = [
  { id: "triangle", name: "Cultural Triangle", subtitle: "Cave temples, rock fortresses and royal reservoirs", photo: "dambulla", brief: "I'd like to explore the Cultural Triangle — Sigiriya and Dambulla" },
  { id: "kandy", name: "Kandy", subtitle: "Lamplit pujas and the start of the hill-country line", photo: "kandy", brief: "I'd like to include Kandy and the Temple of the Tooth" },
  { id: "tea", name: "Tea Country", subtitle: "Planter's bungalows above cloud-filled valleys", photo: "tea", brief: "I'd love time in tea country around Nuwara Eliya" },
  { id: "wild", name: "Wild South", subtitle: "Elephant gatherings, leopards and lagoon birds", photo: "elephants", brief: "We want wildlife — Yala and the elephant gathering" },
  { id: "coast", name: "South Coast", subtitle: "Stilt fishermen, fort towns and quiet villa beaches", photo: "stilt", brief: "A relaxed south coast with Galle and Mirissa" },
] as const satisfies ReadonlyArray<{ id: string; name: string; subtitle: string; photo: PhotoKey; brief: string }>;

export const EDITORIAL = [
  { id: "ella", place: "Ella", title: "Chase the clouds", body: "Climb Little Adam's Peak before breakfast, then walk the tea path to Nine Arches as the morning train curls out of the mist.", photo: "hike", detail: "Uva highlands · 1,041 m" },
  { id: "galle", place: "Galle", title: "Walk the ramparts at golden hour", body: "Inside the fort, the streets are slow and shaded. Up on the walls, the lighthouse catches the last of the sun and the cricket goes on below.", photo: "galle", detail: "Southern Province · UNESCO site" },
  { id: "yala", place: "Yala", title: "Wait for the leopard", body: "The best sightings come to those who leave at first light and are happy to sit with the engine off, listening for the langurs' alarm.", photo: "yala", detail: "Block 1 · dry-zone scrub" },
  { id: "kandy", place: "Kandy", title: "Follow the lamps", body: "At dusk the drums start inside the Temple of the Tooth, and the lakeside fills with white-clad pilgrims carrying lotus flowers.", photo: "kandy", detail: "Central Province · hill capital" },
  { id: "nuwara", place: "Nuwara Eliya", title: "Taste the high country", body: "Walk the pluckers' paths, follow the leaf through a century-old factory, then take tea on a planter's verandah as the valley turns gold.", photo: "tea", detail: "Tea country · 1,868 m" },
] as const satisfies ReadonlyArray<{ id: string; place: string; title: string; body: string; photo: PhotoKey; detail: string }>;

export type Journey = {
  id: string;
  category: string;
  title: string;
  days: number;
  route: string[];
  photo: PhotoKey;
  brief: string;
};

export const JOURNEYS: Journey[] = [
  { id: "hill-country-rail", category: "Rail & tea", title: "The Hill Country Rail", days: 9, route: ["Colombo", "Kandy", "Nuwara Eliya", "Ella"], photo: "train", brief: "9 days by train through tea country: Kandy, Nuwara Eliya and Ella, with tea and hiking" },
  { id: "leopards-lagoons", category: "Wildlife", title: "Leopards & Lagoons", days: 8, route: ["Colombo", "Ella", "Yala", "Mirissa"], photo: "yala", brief: "8 days of wildlife: leopards in Yala, birding and whales off Mirissa" },
  { id: "ancient-kingdoms", category: "Culture", title: "Ancient Kingdoms", days: 7, route: ["Colombo", "Sigiriya", "Kandy"], photo: "dambulla", brief: "7 days of culture and food: Sigiriya, Dambulla cave temples and Kandy" },
  { id: "slow-south", category: "Beaches", title: "The Slow South Coast", days: 6, route: ["Colombo", "Galle", "Mirissa"], photo: "villa", brief: "6 relaxed days on the south coast: Galle Fort and a beach villa near Mirissa, wellness" },
  { id: "family-loop", category: "Family", title: "The Family Island Loop", days: 12, route: ["Colombo", "Sigiriya", "Ella", "Yala", "Galle"], photo: "elephants", brief: "12 days for a family of 4: elephants at Sigiriya, the Ella train, Yala safari and Galle beaches, relaxed" },
];
