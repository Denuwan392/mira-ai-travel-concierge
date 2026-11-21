import type { Stop, StopId } from "./types";

// Route order follows the classic island loop so transfers stay sensible.
export const ROUTE_ORDER: StopId[] = ["sigiriya", "kandy", "nuwara", "ella", "yala", "mirissa", "galle"];

export const RAIL_LINE: StopId[] = ["kandy", "nuwara", "ella"];

export const AIRPORT = { name: "Colombo airport", lat: 7.18, lon: 79.88 };

export const STOPS: Record<StopId, Stop> = {
  sigiriya: {
    id: "sigiriya",
    name: "Sigiriya",
    region: "Cultural Triangle",
    lat: 7.957,
    lon: 80.76,
    photo: "sigiriya",
    headline: "Climb a fortress in the sky",
    scores: { culture: 3, nature: 1, wildlife: 2, adventure: 1, food: 1 },
    activities: [
      { id: "sigiriya-dawn", title: "Dawn climb of Lion Rock", interests: ["culture", "adventure", "nature"], duration: "3–4 hrs", photo: "sigiriya", blurb: "Up the lion's paws before the heat, frescoes and summit gardens to yourself." },
      { id: "minneriya-safari", title: "Minneriya elephant gathering", interests: ["wildlife", "nature"], duration: "Half day", photo: "elephants", blurb: "Afternoon jeep to the reservoir where herds come to graze and bathe." },
      { id: "dambulla-caves", title: "Dambulla cave temples", interests: ["culture"], duration: "2 hrs", photo: "dambulla", blurb: "Five painted caves, a hundred and fifty Buddhas, two thousand years of devotion." },
      { id: "village-cooking", title: "Village kitchen lunch", interests: ["food", "culture"], duration: "3 hrs", photo: "curry", blurb: "Cook rice and curry over a wood fire with a farming family." },
    ],
    hotels: [
      { id: "sig-ecolodge", name: "Jungle-edge eco lodge", kind: "Eco lodge · Sigiriya", photo: "sigiriya", blurb: "Rooms on stilts facing the rock." },
      { id: "sig-lakeside", name: "Lakeside villa", kind: "Villa · Habarana", photo: "elephants", blurb: "Quiet tank views, close to the parks." },
    ],
  },
  kandy: {
    id: "kandy",
    name: "Kandy",
    region: "Hill capital",
    lat: 7.29,
    lon: 80.634,
    photo: "kandy",
    headline: "Follow the lamps to the temple",
    scores: { culture: 3, food: 2, trains: 2, nature: 1 },
    activities: [
      { id: "tooth-puja", title: "Temple of the Tooth evening puja", interests: ["culture"], duration: "2 hrs", photo: "kandy", blurb: "Drums, lotus offerings and lamplight across the lake at dusk." },
      { id: "kandy-cooking", title: "Kandyan home cooking", interests: ["food", "culture"], duration: "3 hrs", photo: "curry", blurb: "Market shop, then a family kitchen for curries and sambols." },
      { id: "peradeniya", title: "Peradeniya botanic gardens", interests: ["nature"], duration: "2–3 hrs", photo: "tea", blurb: "Royal palms, orchid houses and a giant Javan fig." },
    ],
    hotels: [
      { id: "kan-hillside", name: "Hillside boutique house", kind: "Boutique · above Kandy Lake", photo: "kandy", blurb: "Eight rooms, a long view over the city." },
      { id: "kan-walauwa", name: "Heritage walauwa", kind: "Manor house · Kandy outskirts", photo: "bungalow", blurb: "A restored aristocratic home in spice gardens." },
    ],
  },
  nuwara: {
    id: "nuwara",
    name: "Nuwara Eliya",
    region: "Tea country",
    lat: 6.97,
    lon: 80.78,
    photo: "tea",
    headline: "Taste the high country",
    scores: { tea: 3, nature: 2, trains: 2, food: 1 },
    activities: [
      { id: "tea-estate", title: "Tea estate walk and factory", interests: ["tea", "nature", "culture"], duration: "3 hrs", photo: "tea", blurb: "Walk the pluckers' paths, then follow the leaf from wither to cup." },
      { id: "horton-plains", title: "Horton Plains to World's End", interests: ["nature", "adventure"], duration: "Half day", photo: "hike", blurb: "Cloud-forest plateau walk to an 870 m drop." },
      { id: "planter-tea", title: "High tea on a planter's verandah", interests: ["food", "tea"], duration: "2 hrs", photo: "bungalow", blurb: "Scones, single-estate pekoe and the valley going gold." },
    ],
    hotels: [
      { id: "nuw-bungalow", name: "Tea planter's bungalow", kind: "Heritage bungalow · Nuwara Eliya", photo: "bungalow", blurb: "Five suites, butler service, log fires." },
    ],
  },
  ella: {
    id: "ella",
    name: "Ella",
    region: "Uva highlands",
    lat: 6.867,
    lon: 81.046,
    photo: "ella",
    headline: "Chase the clouds",
    scores: { nature: 3, trains: 3, adventure: 2, tea: 1 },
    activities: [
      { id: "little-adams", title: "Sunrise on Little Adam's Peak", interests: ["nature", "adventure"], duration: "2–3 hrs", photo: "hike", blurb: "An easy ridge walk to watch light spill through Ella Gap." },
      { id: "nine-arch", title: "Nine Arch Bridge train crossing", interests: ["trains", "nature"], duration: "2 hrs", photo: "ella", blurb: "Walk the tea path to the viaduct and time it for the morning train." },
      { id: "ella-tea", title: "Uva tea tasting", interests: ["tea", "food"], duration: "2 hrs", photo: "tea", blurb: "Bright Uva-season leaf with a grower who still plucks by hand." },
    ],
    hotels: [
      { id: "ell-cliff", name: "Cliffside eco lodge", kind: "Eco lodge · Ella Gap", photo: "hike", blurb: "Open-sided rooms looking straight down the gap." },
      { id: "ell-estate", name: "Tea estate bungalow", kind: "Estate stay · Haputale", photo: "bungalow", blurb: "A working estate an hour's train from Ella." },
    ],
  },
  yala: {
    id: "yala",
    name: "Yala",
    region: "Southern dry zone",
    lat: 6.372,
    lon: 81.52,
    photo: "yala",
    headline: "Wait for the leopard",
    scores: { wildlife: 3, nature: 2, adventure: 1 },
    activities: [
      { id: "yala-dawn", title: "Dawn leopard safari", interests: ["wildlife", "nature"], duration: "Half day", photo: "yala", blurb: "Gates open at first light, when leopards still use the tracks." },
      { id: "bundala", title: "Bundala wetland birding", interests: ["wildlife", "nature"], duration: "3 hrs", photo: "elephants", blurb: "Flamingos in season, painted storks and crocodile lagoons." },
    ],
    hotels: [
      { id: "yal-camp", name: "Tented camp on the park edge", kind: "Safari camp · Yala buffer", photo: "yala", blurb: "Canvas suites, campfire dinners, early starts." },
    ],
  },
  mirissa: {
    id: "mirissa",
    name: "Mirissa",
    region: "South coast",
    lat: 5.948,
    lon: 80.458,
    photo: "mirissa",
    headline: "Meet the blue whales",
    scores: { beaches: 3, wildlife: 2, wellness: 2 },
    activities: [
      { id: "whale-watch", title: "Blue whale watching at dawn", interests: ["wildlife", "beaches"], duration: "4–5 hrs", photo: "mirissa", blurb: "Out past the shelf where blue whales feed in season." },
      { id: "stilt-fishers", title: "Stilt fishermen at Koggala", interests: ["culture", "beaches"], duration: "2 hrs", photo: "stilt", blurb: "The poles, the patience and the story behind the photograph." },
      { id: "coast-villa-day", title: "Slow day at the villa", interests: ["beaches", "wellness"], duration: "All day", photo: "villa", blurb: "Pool, sea, an Ayurvedic massage and nothing on the clock." },
    ],
    hotels: [
      { id: "mir-clifftop", name: "Clifftop villa", kind: "Private villa · near Tangalle", photo: "villa", blurb: "Infinity pool, frangipani, the ocean on three sides." },
      { id: "mir-beachhouse", name: "Beach house", kind: "Boutique · Mirissa bay", photo: "stilt", blurb: "Steps from the sand, a short walk to the harbour." },
    ],
  },
  galle: {
    id: "galle",
    name: "Galle",
    region: "Fort city",
    lat: 6.026,
    lon: 80.217,
    photo: "galle",
    headline: "Walk the ramparts at golden hour",
    scores: { culture: 3, beaches: 2, food: 2 },
    activities: [
      { id: "fort-ramparts", title: "Galle Fort ramparts at golden hour", interests: ["culture", "beaches"], duration: "2 hrs", photo: "galle", blurb: "Lighthouse, bastions and cricket on the green below." },
      { id: "galle-cooking", title: "Southern spice cooking class", interests: ["food"], duration: "3 hrs", photo: "curry", blurb: "Black pork, ambul thiyal and the art of goraka." },
      { id: "galle-stilt", title: "Sunset with the stilt fishermen", interests: ["culture", "beaches"], duration: "2 hrs", photo: "stilt", blurb: "A short drive along the coast as the poles turn to silhouette." },
    ],
    hotels: [
      { id: "gal-mansion", name: "Restored Dutch mansion", kind: "Boutique · inside Galle Fort", photo: "galle", blurb: "Courtyard pool, teak floors, walk everywhere." },
    ],
  },
};

const ALIASES: Array<[RegExp, StopId]> = [
  [/\bsigiriya|sigiri|lion rock|dambulla|habarana|minneriya|cultural triangle|polonnaruwa/, "sigiriya"],
  [/\bkandy\b/, "kandy"],
  [/nuwara\s*eliya|nuwara|tea country|horton plains/, "nuwara"],
  [/\bella\b|haputale|nine arch/, "ella"],
  [/\byala\b|leopard/, "yala"],
  [/mirissa|tangalle|weligama/, "mirissa"],
  [/\bgalle\b|unawatuna/, "galle"],
];

export function findStops(text: string): StopId[] {
  const t = text.toLowerCase();
  const found: StopId[] = [];
  for (const [re, id] of ALIASES) if (re.test(t) && !found.includes(id)) found.push(id);
  return found;
}

export function findStop(text: string): StopId | null {
  return findStops(text)[0] ?? null;
}
