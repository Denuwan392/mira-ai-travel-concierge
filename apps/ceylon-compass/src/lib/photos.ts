// Location photography. Each entry is replaceable: swap the import, keep the alt text accurate.
import sigiriya from "@/assets/photos/sigiriya.jpg";
import ella from "@/assets/photos/ella.jpg";
import galle from "@/assets/photos/galle.jpg";
import yala from "@/assets/photos/yala.jpg";
import mirissa from "@/assets/photos/mirissa.jpg";
import train from "@/assets/photos/train.jpg";
import tea from "@/assets/photos/tea.jpg";
import kandy from "@/assets/photos/kandy.jpg";
import dambulla from "@/assets/photos/dambulla.jpg";
import stilt from "@/assets/photos/stilt.jpg";
import hike from "@/assets/photos/hike.jpg";
import curry from "@/assets/photos/curry.jpg";
import bungalow from "@/assets/photos/bungalow.jpg";
import elephants from "@/assets/photos/elephants.jpg";
import villa from "@/assets/photos/villa.jpg";
import sigiriyaAerial2k from "@/assets/photos/sigiriya-aerial-2k.jpg";
import nineArchesTrain2k from "@/assets/photos/nine-arches-train-2k.jpg";
import nineArchesBridge2k from "@/assets/photos/nine-arches-bridge-2k.jpg";
import galleLighthouse2k from "@/assets/photos/galle-lighthouse-2k.jpg";
import galleRamparts2k from "@/assets/photos/galle-ramparts-2k.jpg";
import coastPalms2k from "@/assets/photos/coast-palms-2k.jpg";
import landscapeArch2k from "@/assets/photos/ceylon-landscape-architecture-2k.jpg";

export type Photo = { src: string; alt: string };

export const photos = {
  sigiriya: { src: sigiriya, alt: "Sigiriya Lion Rock glowing at sunrise above misty jungle" },
  ella: { src: ella, alt: "Blue train crossing the Nine Arch Bridge in Ella through morning mist" },
  galle: { src: galle, alt: "Galle Fort lighthouse and ramparts at golden hour" },
  yala: { src: yala, alt: "Leopard resting on a granite boulder in Yala National Park" },
  mirissa: { src: mirissa, alt: "Whale tail rising from the sea off Mirissa at dawn" },
  train: { src: train, alt: "Traveller sitting in an open train doorway above tea plantations" },
  tea: { src: tea, alt: "Tea plucker with a basket on the misty slopes of Nuwara Eliya" },
  kandy: { src: kandy, alt: "Temple of the Tooth reflected in Kandy Lake at dusk" },
  dambulla: { src: dambulla, alt: "Golden Buddha statues beneath painted ceilings in Dambulla cave temple" },
  stilt: { src: stilt, alt: "Stilt fishermen silhouetted at sunset on the south coast" },
  hike: { src: hike, alt: "Hikers on the Little Adam's Peak ridge above Ella Gap at sunrise" },
  curry: { src: curry, alt: "Home cook serving Sri Lankan rice and curry on a banana leaf" },
  bungalow: { src: bungalow, alt: "Tea planter's bungalow verandah overlooking misty valleys" },
  elephants: { src: elephants, alt: "Wild elephants gathering at Minneriya reservoir at sunset" },
  villa: { src: villa, alt: "Beachfront villa pool meeting the Indian Ocean at sunset" },
  sigiriyaAerial: { src: sigiriyaAerial2k, alt: "Aerial view of Sigiriya Rock Fortress rising above the jungle" },
  nineArchesTrain: { src: nineArchesTrain2k, alt: "Train crossing the historic Nine Arches Bridge in Ella" },
  nineArchesBridge: { src: nineArchesBridge2k, alt: "Scenic view of the Nine Arches Bridge surrounded by lush tea hills" },
  galleLighthouse: { src: galleLighthouse2k, alt: "Galle Fort lighthouse overlooking the Indian Ocean coast" },
  galleRamparts: { src: galleRamparts2k, alt: "Historic stone ramparts and bastion of Galle Fort" },
  coastPalms: { src: coastPalms2k, alt: "Tropical coastline lined with coconut palms and turquoise water" },
  landscapeArch: { src: landscapeArch2k, alt: "Sri Lankan tropical landscape and traditional architecture" },
} satisfies Record<string, Photo>;

export type PhotoKey = keyof typeof photos;

export const destinationPhotos: Record<string, PhotoKey> = {
  D01: "sigiriya",
  D02: "elephants",
  D03: "kandy",
  D04: "tea",
  D05: "ella",
  D07: "galle",
  D08: "mirissa",
  D06: "yala",
};
