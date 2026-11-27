import React, { useState, useEffect, useLayoutEffect, useRef, useCallback, createContext, useContext } from "react";
import { createRoot } from "react-dom/client";
import { useConversation } from "./useConversation";
import { api, session } from "@/lib/live/service";
import { RouteMap } from "@/components/plan/RouteMap";
import { destinationPhotos, photos } from "@/lib/photos";
import { StaffConsole } from "@/components/staff/StaffConsole";
import { MarkdownContent } from "@/components/plan/MarkdownContent";
import { DestinationShowcase } from "@/components/home/DestinationShowcase";
import "./style.css";
import {
  MapPin, Calendar, Users, Clock, ChevronRight, ChevronDown, ChevronLeft,
  Search, Menu, X, Send, Compass, Star, Heart, Globe, Phone, Mail,
  ArrowRight, ArrowLeft, Check, Info, AlertCircle, Sparkles, MessageCircle,
  Sun, TreePine, Waves, Building, Mountain, Camera, Shield, BookOpen,
  Plus, Minus, Filter, ExternalLink, Quote, Navigation, Plane, Tent,
  User, Lock, Eye, EyeOff, LogOut, CheckCircle, FileText, Loader2
} from "lucide-react";

// ============ INITIAL DATA ============
const INITIAL_TOURS = [
  {
    "id": "T01",
    "slug": "sigiriya-minneriya-day-tour-from-kandy",
    "title": "Sigiriya and Minneriya Day Tour from Kandy",
    "category": "Day tour",
    "duration": "1 day",
    "start": "Your hotel in Kandy",
    "destinations": [
      "sigiriya",
      "minneriya"
    ],
    "description": "A long, rewarding day from Kandy into the Cultural Triangle: climb the Sigiriya rock fortress in the morning, then look for wild elephants on an afternoon jeep safari in Minneriya National Park.",
    "accent": "brand-orange",
    "imgClass": "tour-img-t01 tour-img-1",
    "itinerary": [
      {
        "day": 1,
        "title": "Sigiriya and Minneriya Day Tour from Kandy",
        "description": "A long, rewarding day from Kandy into the Cultural Triangle: climb the Sigiriya rock fortress in the morning, then look for wild elephants on an afternoon jeep safari in Minneriya National Park."
      }
    ],
    "inclusions": {
      "included": [
        "Pick-up and drop-off at your Kandy hotel",
        "Private air-conditioned vehicle and English-speaking guide",
        "Sigiriya entrance and Minneriya park entrance with safari jeep",
        "Lunch and bottled water"
      ],
      "optional": [
        "Optional activities and upgrades"
      ],
      "not_included": [
        "Personal expenses",
        "Tips and gratuities"
      ]
    }
  },
  {
    "id": "T02",
    "slug": "kandy-city-tour",
    "title": "Kandy City Tour",
    "category": "City tour",
    "duration": "1 day",
    "start": "Your hotel in Kandy",
    "destinations": [
      "kandy"
    ],
    "description": "A full day around Sri Lanka's last royal capital: Kandy Lake, the market, a gem museum, the Peradeniya botanical gardens and the Temple of the Sacred Tooth Relic, ending with a Kandyan dance show.",
    "accent": "brand-teal",
    "imgClass": "tour-img-t02 tour-img-2",
    "itinerary": [
      {
        "day": 1,
        "title": "Kandy City Tour",
        "description": "A full day around Sri Lanka's last royal capital: Kandy Lake, the market, a gem museum, the Peradeniya botanical gardens and the Temple of the Sacred Tooth Relic, ending with a Kandyan dance show."
      }
    ],
    "inclusions": {
      "included": [
        "Private vehicle and guide",
        "Entrance to the temple, Peradeniya gardens and the cultural show",
        "Lunch"
      ],
      "optional": [
        "Optional activities and upgrades"
      ],
      "not_included": [
        "Personal expenses",
        "Tips and gratuities"
      ]
    }
  },
  {
    "id": "T03",
    "slug": "colombo-city-tour",
    "title": "Colombo City Tour",
    "category": "City tour",
    "duration": "1 day",
    "start": "Your hotel in Colombo or Negombo",
    "destinations": [
      "colombo"
    ],
    "description": "Colombo's landmarks in a day: the Fort district, the Old Parliament, Independence Square, Gangaramaya Temple, Viharamahadevi Park and Galle Face Green, with free time for shopping at the end.",
    "accent": "brand-orange",
    "imgClass": "tour-img-t03 tour-img-3",
    "itinerary": [
      {
        "day": 1,
        "title": "Colombo City Tour",
        "description": "Colombo's landmarks in a day: the Fort district, the Old Parliament, Independence Square, Gangaramaya Temple, Viharamahadevi Park and Galle Face Green, with free time for shopping at the end."
      }
    ],
    "inclusions": {
      "included": [
        "Private vehicle and guide",
        "Temple entrance",
        "Lunch"
      ],
      "optional": [
        "Optional activities and upgrades"
      ],
      "not_included": [
        "Personal expenses",
        "Tips and gratuities"
      ]
    }
  },
  {
    "id": "T04",
    "slug": "galle-fort-walking-tour",
    "title": "Galle Fort Walking Tour",
    "category": "City tour",
    "duration": "Half day",
    "start": "Galle Fort main gate",
    "destinations": [
      "galle"
    ],
    "description": "Explore the ramparts, bastions, churches and cobbled lanes of Galle's 17th-century fort on foot, with time for its boutiques and caf\u00e9s.",
    "accent": "brand-teal",
    "imgClass": "tour-img-t04 tour-img-4",
    "itinerary": [
      {
        "day": 1,
        "title": "Galle Fort Walking Tour",
        "description": "Explore the ramparts, bastions, churches and cobbled lanes of Galle's 17th-century fort on foot, with time for its boutiques and caf\u00e9s."
      }
    ],
    "inclusions": {
      "included": [
        "Guide",
        "Transfers from hotels in Galle, Unawatuna or Hikkaduwa",
        "Lunch at a caf\u00e9 inside the fort"
      ],
      "optional": [
        "Optional activities and upgrades"
      ],
      "not_included": [
        "Personal expenses",
        "Tips and gratuities"
      ]
    }
  },
  {
    "id": "T05",
    "slug": "mirissa-whale-dolphin-watching",
    "title": "Whale and Dolphin Watching Tour in Mirissa",
    "category": "Day tour",
    "duration": "1 day",
    "start": "Your beach hotel on the south or south-west coast",
    "destinations": [
      "mirissa"
    ],
    "description": "An early boat trip out of Mirissa harbour to look for blue whales, sperm whales and spinner dolphins, returning to your beach hotel by early afternoon.",
    "accent": "brand-orange",
    "imgClass": "tour-img-t05 tour-img-5",
    "itinerary": [
      {
        "day": 1,
        "title": "Whale and Dolphin Watching Tour in Mirissa",
        "description": "An early boat trip out of Mirissa harbour to look for blue whales, sperm whales and spinner dolphins, returning to your beach hotel by early afternoon."
      }
    ],
    "inclusions": {
      "included": [
        "Transfers from your beach hotel",
        "Shared whale-watching boat with life jackets",
        "Light breakfast on board and lunch on return"
      ],
      "optional": [
        "Optional activities and upgrades"
      ],
      "not_included": [
        "Personal expenses",
        "Tips and gratuities"
      ]
    }
  },
  {
    "id": "T06",
    "slug": "kandy-nuwara-eliya-train-day-tour",
    "title": "Train and Day Tour from Kandy to Nuwara Eliya",
    "category": "Day tour",
    "duration": "1 night / 2 days",
    "start": "Your hotel in Kandy",
    "destinations": [
      "kandy",
      "nuwara-eliya"
    ],
    "description": "Take the morning hill-country train from Kandy through misty tea estates, then explore Nuwara Eliya, the town known as \"Little England\".",
    "accent": "brand-teal",
    "imgClass": "tour-img-t06 tour-img-6",
    "itinerary": [
      {
        "day": 1,
        "title": "Train and Day Tour from Kandy to Nuwara Eliya",
        "description": "Take the morning hill-country train from Kandy through misty tea estates, then explore Nuwara Eliya, the town known as \"Little England\"."
      }
    ],
    "inclusions": {
      "included": [
        "Second-class train ticket, Kandy to Nanu Oya",
        "High tea",
        "Private vehicle and guide; pick-up and drop-off in Kandy",
        "Tea-factory entrance"
      ],
      "optional": [
        "Optional activities and upgrades"
      ],
      "not_included": [
        "Personal expenses",
        "Tips and gratuities"
      ]
    }
  },
  {
    "id": "T07",
    "slug": "kandy-heritage-stay",
    "title": "Kandy Heritage Stay",
    "category": "Short stay",
    "duration": "2 nights / 3 days",
    "start": "Kandy",
    "destinations": [
      "kandy"
    ],
    "description": "A short, unhurried stay in Kandy in a colonial-era hotel by the lake, with a city tour, the Temple of the Tooth and a cultural show.",
    "accent": "brand-orange",
    "imgClass": "tour-img-t07 tour-img-1",
    "itinerary": [
      {
        "day": 1,
        "title": "Arrive in Kandy",
        "description": "Check in and walk around Kandy Lake. Evening visit to the Temple of the Tooth.\n\n- Meals: Dinner\n- Accommodation: Hotel Suisse or similar\n- Entrance tickets included: Temple of the Tooth\n- Other inclusions: Air-conditioned vehicle and English-speaking guide"
      },
      {
        "day": 2,
        "title": "Kandy city tour",
        "description": "Peradeniya gardens, the market and a gem museum. Kandyan dance show in the evening.\n\n- Meals: Breakfast, lunch, dinner\n- Accommodation: Hotel Suisse or similar\n- Entrance tickets included: Peradeniya gardens, cultural show\n- Other inclusions: Air-conditioned vehicle and English-speaking guide"
      },
      {
        "day": 3,
        "title": "Departure",
        "description": "Free morning, then drop-off anywhere in Kandy.\n\n- Meals: Breakfast\n- Accommodation: None\n- Entrance tickets included: None\n- Other inclusions: Air-conditioned vehicle and English-speaking guide"
      }
    ],
    "inclusions": {
      "included": [
        "Accommodation as listed, or a hotel of the same class if it is unavailable (confirmed at booking)",
        "Meals as listed for each day",
        "Private air-conditioned vehicle throughout",
        "English-speaking guide",
        "Entrance tickets for the sites listed, except those marked *optional*",
        "Two 500 ml bottles of water per person per day",
        "24-hour emergency line"
      ],
      "optional": [
        "Optional activities and upgrades"
      ],
      "not_included": [
        "Personal expenses",
        "Tips and gratuities"
      ]
    }
  },
  {
    "id": "T08",
    "slug": "highlights-of-sri-lanka-7-nights",
    "title": "Highlights of Sri Lanka",
    "category": "Round trip",
    "duration": "7 nights / 8 days",
    "start": "Bandaranaike International Airport (CMB)",
    "destinations": [
      "sigiriya",
      "minneriya",
      "kandy",
      "nuwara-eliya",
      "galle",
      "colombo"
    ],
    "description": "For first-time visitors who want to see a bit of everything: the Cultural Triangle, wild elephants, the hill country by train, the south coast and Colombo.",
    "accent": "brand-teal",
    "imgClass": "tour-img-t08 tour-img-2",
    "itinerary": [
      {
        "day": 1,
        "title": "Airport to Negombo",
        "description": "Meet and greet at the airport and transfer to Negombo.\n\n- Meals: None\n- Accommodation: Suriya Resort, Amaluna or similar\n- Entrance tickets included: None\n- Other inclusions: Air-conditioned vehicle and English-speaking guide"
      },
      {
        "day": 2,
        "title": "Negombo to Sigiriya",
        "description": "Dambulla cave temple, then an evening jeep safari in Minneriya National Park.\n\n- Meals: Breakfast, dinner\n- Accommodation: Sigiriya Village, Oak Ray Elephant Lake or similar\n- Entrance tickets included: Dambulla cave temple, Minneriya safari\n- Other inclusions: Air-conditioned vehicle and English-speaking guide"
      },
      {
        "day": 3,
        "title": "Sigiriya and Polonnaruwa",
        "description": "Climb Sigiriya at sunrise, village tour with lunch on lotus leaves, afternoon at Polonnaruwa.\n\n- Meals: Breakfast, lunch, dinner\n- Accommodation: Sigiriya Village, Oak Ray Elephant Lake or similar\n- Entrance tickets included: Sigiriya, village tour, Polonnaruwa\n- Other inclusions: Air-conditioned vehicle and English-speaking guide"
      },
      {
        "day": 4,
        "title": "Sigiriya to Kandy",
        "description": "Spice garden, Kandy city tour, Temple of the Tooth and a cultural show.\n\n- Meals: Breakfast, dinner\n- Accommodation: Hotel Suisse, Hotel Topaz or similar\n- Entrance tickets included: Spice garden, Temple of the Tooth, cultural show\n- Other inclusions: Air-conditioned vehicle and English-speaking guide"
      },
      {
        "day": 5,
        "title": "Train to Nuwara Eliya",
        "description": "Scenic train from Kandy to Nanu Oya, tea factory visit, Nuwara Eliya city tour.\n\n- Meals: Breakfast, dinner\n- Accommodation: Heaven Seven or similar\n- Entrance tickets included: Train ticket (2nd class), tea factory\n- Other inclusions: Air-conditioned vehicle and English-speaking guide"
      },
      {
        "day": 6,
        "title": "Nuwara Eliya to the south-west coast",
        "description": "Long drive to the coast. *Optional:* white-water rafting or a jungle walk at Kitulgala on the way.\n\n- Meals: Breakfast, dinner\n- Accommodation: Hikka Tranz by Cinnamon, Avani Kalutara or similar\n- Entrance tickets included: None\n- Other inclusions: Air-conditioned vehicle and English-speaking guide"
      },
      {
        "day": 7,
        "title": "South coast",
        "description": "Madu River mangrove boat safari, turtle hatchery, stilt fishermen and Galle Fort.\n\n- Meals: Breakfast, dinner\n- Accommodation: Hikka Tranz by Cinnamon, Avani Kalutara or similar\n- Entrance tickets included: Madu River safari, turtle hatchery, Galle Fort\n- Other inclusions: Air-conditioned vehicle and English-speaking guide"
      },
      {
        "day": 8,
        "title": "Colombo and departure",
        "description": "Colombo city tour and shopping, then drop-off at the airport.\n\n- Meals: Breakfast\n- Accommodation: None\n- Entrance tickets included: Colombo city tour\n- Other inclusions: Air-conditioned vehicle and English-speaking guide"
      }
    ],
    "inclusions": {
      "included": [
        "Accommodation as listed, or a hotel of the same class if it is unavailable (confirmed at booking)",
        "Meals as listed for each day",
        "Private air-conditioned vehicle throughout",
        "English-speaking guide",
        "Entrance tickets for the sites listed, except those marked *optional*",
        "Two 500 ml bottles of water per person per day",
        "24-hour emergency line"
      ],
      "optional": [
        "Optional activities and upgrades"
      ],
      "not_included": [
        "Personal expenses",
        "Tips and gratuities"
      ]
    }
  },
  {
    "id": "T09",
    "slug": "cultural-triangle-6-nights",
    "title": "Cultural Triangle Sri Lanka Package",
    "category": "Round trip",
    "duration": "6 nights / 7 days",
    "start": "Colombo or Negombo",
    "destinations": [
      "anuradhapura",
      "sigiriya",
      "kandy"
    ],
    "description": "The ancient kingdoms in a week: Anuradhapura, Polonnaruwa, the Sigiriya rock fortress, the Dambulla cave temple and the last royal capital, Kandy.",
    "accent": "brand-orange",
    "imgClass": "tour-img-t09 tour-img-3",
    "itinerary": [
      {
        "day": 1,
        "title": "Colombo to Anuradhapura",
        "description": "Drive north and visit Wilpattu's edge villages on the way.\n\n- Meals: Dinner\n- Accommodation: Anuradhapura Heritage Lodge or similar\n- Entrance tickets included: None\n- Other inclusions: Air-conditioned vehicle and English-speaking guide"
      },
      {
        "day": 2,
        "title": "Anuradhapura",
        "description": "The sacred city by bicycle: Sri Maha Bodhi, Ruwanwelisaya and the great dagobas.\n\n- Meals: Breakfast, lunch, dinner\n- Accommodation: Anuradhapura Heritage Lodge or similar\n- Entrance tickets included: Anuradhapura sacred city\n- Other inclusions: Air-conditioned vehicle and English-speaking guide"
      },
      {
        "day": 3,
        "title": "Anuradhapura to Sigiriya",
        "description": "Mihintale on the way, afternoon village tour.\n\n- Meals: Breakfast, dinner\n- Accommodation: Sigiriya Village or similar\n- Entrance tickets included: Mihintale, village tour\n- Other inclusions: Air-conditioned vehicle and English-speaking guide"
      },
      {
        "day": 4,
        "title": "Sigiriya and Polonnaruwa",
        "description": "Sigiriya at sunrise, Polonnaruwa in the afternoon.\n\n- Meals: Breakfast, dinner\n- Accommodation: Sigiriya Village or similar\n- Entrance tickets included: Sigiriya, Polonnaruwa\n- Other inclusions: Air-conditioned vehicle and English-speaking guide"
      },
      {
        "day": 5,
        "title": "Dambulla to Kandy",
        "description": "Dambulla cave temple and a spice garden, evening at the Temple of the Tooth.\n\n- Meals: Breakfast, dinner\n- Accommodation: Hotel Suisse, Hotel Topaz or similar\n- Entrance tickets included: Dambulla, spice garden, Temple of the Tooth\n- Other inclusions: Air-conditioned vehicle and English-speaking guide"
      },
      {
        "day": 6,
        "title": "Kandy",
        "description": "Peradeniya gardens and a Kandyan dance show.\n\n- Meals: Breakfast, dinner\n- Accommodation: Hotel Suisse, Hotel Topaz or similar\n- Entrance tickets included: Peradeniya gardens, cultural show\n- Other inclusions: Air-conditioned vehicle and English-speaking guide"
      },
      {
        "day": 7,
        "title": "Kandy to Colombo",
        "description": "Drive back to Colombo or the airport.\n\n- Meals: Breakfast\n- Accommodation: None\n- Entrance tickets included: None\n- Other inclusions: Air-conditioned vehicle and English-speaking guide"
      }
    ],
    "inclusions": {
      "included": [
        "Accommodation as listed, or a hotel of the same class if it is unavailable (confirmed at booking)",
        "Meals as listed for each day",
        "Private air-conditioned vehicle throughout",
        "English-speaking guide",
        "Entrance tickets for the sites listed, except those marked *optional*",
        "Two 500 ml bottles of water per person per day",
        "24-hour emergency line"
      ],
      "optional": [
        "Optional activities and upgrades"
      ],
      "not_included": [
        "Personal expenses",
        "Tips and gratuities"
      ]
    }
  },
  {
    "id": "T10",
    "slug": "instafamous-sri-lanka",
    "title": "Instafamous Sri Lanka",
    "category": "Round trip",
    "duration": "10 nights / 11 days",
    "start": "Bandaranaike International Airport (CMB)",
    "destinations": [
      "sigiriya",
      "kandy",
      "ella",
      "mirissa",
      "galle"
    ],
    "description": "Eleven days of the island's most photographed places: Sigiriya at sunrise, the Nine Arches Bridge, the Kandy to Ella train, Coconut Tree Hill in Mirissa and Galle Fort's lighthouse at dusk. We plan every stop around the best light.",
    "accent": "brand-teal",
    "imgClass": "tour-img-t10 tour-img-4",
    "itinerary": [],
    "inclusions": {
      "included": [
        "Private air-conditioned transport",
        "English-speaking driver-guide",
        "Sightseeing as described"
      ],
      "optional": [
        "Optional activities and upgrades"
      ],
      "not_included": [
        "Personal expenses",
        "Tips and gratuities"
      ]
    }
  },
  {
    "id": "T11",
    "slug": "sri-lanka-beach-stay-mirissa",
    "title": "Sri Lanka Beach Stay \u2013 Mirissa",
    "category": "Beach stay",
    "duration": "6 nights / 7 days",
    "start": "Bandaranaike International Airport (CMB)",
    "destinations": [
      "mirissa"
    ],
    "description": "Sun, sand and sea for a week: six nights at a beachfront villa resort in Mirissa with breakfast and dinner, airport transfers and a chauffeur on call for short trips.",
    "accent": "brand-orange",
    "imgClass": "tour-img-t11 tour-img-5",
    "itinerary": [
      {
        "day": 1,
        "title": "Sri Lanka Beach Stay \u2013 Mirissa",
        "description": "Sun, sand and sea for a week: six nights at a beachfront villa resort in Mirissa with breakfast and dinner, airport transfers and a chauffeur on call for short trips."
      }
    ],
    "inclusions": {
      "included": [
        "6 nights at Mirissa Bay Villas or similar, breakfast and dinner",
        "Airport transfers and a chauffeur-driven vehicle",
        "*Optional:* whale watching (November to April)"
      ],
      "optional": [
        "Optional activities and upgrades"
      ],
      "not_included": [
        "Personal expenses",
        "Tips and gratuities"
      ]
    }
  },
  {
    "id": "T12",
    "slug": "treasures-of-sri-lanka",
    "title": "Treasures of Sri Lanka",
    "category": "Round trip",
    "duration": "13 nights / 14 days",
    "start": "Bandaranaike International Airport (CMB)",
    "destinations": [
      "anuradhapura",
      "sigiriya",
      "kandy",
      "nuwara-eliya",
      "ella",
      "yala",
      "galle"
    ],
    "description": "Our grand tour: ancient cities, temples, tea hills, the hill-country train, a leopard safari and the southern coast in two unhurried weeks.",
    "accent": "brand-teal",
    "imgClass": "tour-img-t12 tour-img-6",
    "itinerary": [
      {
        "day": 1,
        "title": "Negombo",
        "description": "Suriya Resort or similar"
      },
      {
        "day": 2,
        "title": "Anuradhapura",
        "description": "Anuradhapura Heritage Lodge or similar"
      },
      {
        "day": 3,
        "title": "Sigiriya (2 nights)",
        "description": "Sigiriya Village or similar"
      },
      {
        "day": 4,
        "title": "Kandy (2 nights)",
        "description": "Hotel Suisse or similar"
      },
      {
        "day": 5,
        "title": "Nuwara Eliya",
        "description": "Heritance Tea Factory (no substitute; this is a signature stay)"
      },
      {
        "day": 6,
        "title": "Ella (2 nights)",
        "description": "Ella Gap View Lodge or similar"
      },
      {
        "day": 7,
        "title": "Yala",
        "description": "Cinnamon Wild Yala or similar"
      },
      {
        "day": 8,
        "title": "Galle (2 nights)",
        "description": "Galle Fort Hotel or similar"
      },
      {
        "day": 9,
        "title": "Hikkaduwa",
        "description": "Hikka Tranz by Cinnamon or similar"
      }
    ],
    "inclusions": {
      "included": [
        "Accommodation as listed, or a hotel of the same class if it is unavailable (confirmed at booking)",
        "Meals as listed for each day",
        "Private air-conditioned vehicle throughout",
        "English-speaking guide",
        "Entrance tickets for the sites listed, except those marked *optional*",
        "Two 500 ml bottles of water per person per day",
        "24-hour emergency line"
      ],
      "optional": [
        "Optional activities and upgrades"
      ],
      "not_included": [
        "Personal expenses",
        "Tips and gratuities"
      ]
    }
  },
  {
    "id": "T13",
    "slug": "wildlife-photography-tour",
    "title": "Wildlife Photography Tour",
    "category": "Special interest",
    "duration": "6 nights / 7 days",
    "start": "Colombo",
    "destinations": [
      "yala"
    ],
    "description": "For photographers: elephants at Udawalawe, leopards and sloth bears at Yala, and water birds at Bundala, with a naturalist who knows where the light is.",
    "accent": "brand-orange",
    "imgClass": "tour-img-t13 tour-img-1",
    "itinerary": [],
    "inclusions": {
      "included": [
        "Accommodation as listed, or a hotel of the same class if it is unavailable (confirmed at booking)",
        "Meals as listed for each day",
        "Private air-conditioned vehicle throughout",
        "English-speaking guide",
        "Entrance tickets for the sites listed, except those marked *optional*",
        "Two 500 ml bottles of water per person per day",
        "24-hour emergency line"
      ],
      "optional": [
        "Optional activities and upgrades"
      ],
      "not_included": [
        "Personal expenses",
        "Tips and gratuities"
      ]
    }
  },
  {
    "id": "T16",
    "slug": "cultural-triangle-tour-5-nights",
    "title": "Cultural Triangle Tour",
    "category": "Round trip",
    "duration": "5 nights / 6 days",
    "start": "Colombo",
    "destinations": [
      "sigiriya",
      "kandy"
    ],
    "description": "Five nights through Sigiriya, Polonnaruwa, Dambulla and Kandy, with an elephant safari at Kaudulla.",
    "accent": "brand-teal",
    "imgClass": "tour-img-t16 tour-img-2",
    "itinerary": [],
    "inclusions": {
      "included": [
        "Private air-conditioned transport",
        "English-speaking driver-guide",
        "Sightseeing as described"
      ],
      "optional": [
        "Optional activities and upgrades"
      ],
      "not_included": [
        "Personal expenses",
        "Tips and gratuities"
      ]
    }
  }
];

const INITIAL_DESTINATIONS = [
  {
    "id": "D09",
    "slug": "anuradhapura",
    "title": "Anuradhapura",
    "description": "Sri Lanka's first great capital, founded in the 4th century BCE. Its sacred city holds the Sri Maha Bodhi tree and vast dagobas such as Ruwanwelisaya. It is best explored by bicycle.",
    "imgClass": "destination-img-anuradhapura",
    "accent": "brand-teal"
  },
  {
    "id": "D10",
    "slug": "colombo",
    "title": "Colombo",
    "description": "Sri Lanka's commercial capital: the colonial Fort district, Pettah's markets, Gangaramaya Temple and the seafront at Galle Face Green.",
    "imgClass": "destination-img-colombo",
    "accent": "brand-sun"
  },
  {
    "id": "D05",
    "slug": "ella",
    "title": "Ella",
    "description": "A relaxed hill town known for the Nine Arches Bridge, Little Adam's Peak and some of the most scenic stretches of the hill-country railway.",
    "imgClass": "destination-img-ella",
    "accent": "brand-teal"
  },
  {
    "id": "D07",
    "slug": "galle",
    "title": "Galle",
    "description": "Galle Fort is a walled 17th-century town on the south-west coast and a UNESCO World Heritage Site, full of boutique hotels, caf\u00e9s, galleries and churches.",
    "imgClass": "destination-img-galle",
    "accent": "brand-sky"
  },
  {
    "id": "D03",
    "slug": "kandy",
    "title": "Kandy",
    "description": "Kandy was the last royal capital of Sri Lanka. The Temple of the Sacred Tooth Relic sits beside a calm lake ringed by hills. The Royal Botanical Gardens at Peradeniya are just outside the city.",
    "imgClass": "destination-img-kandy",
    "accent": "brand-leaf"
  },
  {
    "id": "D02",
    "slug": "minneriya",
    "title": "Minneriya National Park",
    "description": "Minneriya is famous for \"the gathering\": in the dry season, roughly August to October, hundreds of elephants come to the shrinking reservoir to drink and graze. Safaris are by jeep in the late afternoon.",
    "imgClass": "destination-img-minneriya",
    "accent": "brand-leaf"
  },
  {
    "id": "D08",
    "slug": "mirissa",
    "title": "Mirissa",
    "description": "Mirissa is a crescent-shaped beach on the south coast, known for blue-whale and dolphin watching between November and April, surf breaks and Coconut Tree Hill at sunset.",
    "imgClass": "destination-img-mirissa",
    "accent": "brand-coral"
  },
  {
    "id": "D04",
    "slug": "nuwara-eliya",
    "title": "Nuwara Eliya",
    "description": "At about 1,900 metres, Nuwara Eliya is the heart of tea country, with a cool climate, colonial buildings, Lake Gregory and a golf course. Nights can be cold.",
    "imgClass": "destination-img-nuwara-eliya",
    "accent": "brand-teal"
  },
  {
    "id": "D01",
    "slug": "sigiriya",
    "title": "Sigiriya",
    "description": "The rock fortress of Sigiriya rises about 200 metres above the plains of the Cultural Triangle. King Kashyapa built his palace on the summit in the 5th century; its frescoes and Lion Gate are among Sri Lanka's best-known sights. The neighbouring Dambulla cave temple is a short drive away.",
    "imgClass": "destination-img-sigiriya",
    "accent": "brand-sun"
  },
  {
    "id": "D06",
    "slug": "yala",
    "title": "Yala National Park",
    "description": "Yala, in the dry south-east, has one of the highest densities of leopards in the world, as well as elephants, sloth bears, crocodiles and over 200 bird species. Safaris run at dawn and in the late afternoon.",
    "imgClass": "destination-img-yala",
    "accent": "brand-coral"
  }
];


const TRAVEL_STYLES = [
  { title: 'Culture & Heritage', icon: Building, color: 'brand-teal', description: 'Ancient cities, temples and sacred sites' },
  { title: 'Wildlife & Nature', icon: TreePine, color: 'brand-leaf', description: 'Safaris, national parks and rainforests' },
  { title: 'Scenic Hill Country', icon: Mountain, color: 'brand-teal', description: 'Tea plantations, misty peaks and waterfalls' },
  { title: 'Beach Escapes', icon: Waves, color: 'brand-sky', description: 'Tropical coasts, surfing and whale watching' },
  { title: 'City & Day Tours', icon: Compass, color: 'brand-orange', description: 'Colombo, Kandy and cultural experiences' },
  { title: 'Multi-day Adventures', icon: Tent, color: 'brand-coral', description: 'Complete journeys across the island' },
];

const POLICIES = [
  {
    "slug": "about-us",
    "title": "About Ceylon Compass Holidays",
    "id": "P05"
  },
  {
    "slug": "booking-and-payment",
    "title": "Booking and payment",
    "id": "P01"
  },
  {
    "slug": "cancellation-policy",
    "title": "Cancellation policy",
    "id": "P02"
  },
  {
    "slug": "children-and-infants",
    "title": "Children and infants",
    "id": "P03"
  },
  {
    "slug": "faq",
    "title": "Frequently asked questions",
    "id": "P04"
  },
  {
    "slug": "testimonials",
    "title": "What our guests say",
    "id": "P06"
  },
  {
    "slug": "booking-payment",
    "title": "Booking and payment",
    "id": "P01"
  },
  {
    "slug": "cancellation",
    "title": "Cancellation policy",
    "id": "P02"
  },
  {
    "slug": "children-infants",
    "title": "Children and infants",
    "id": "P03"
  }
];

const POLICY_CONTENT = {
  "about-us": {
    "id": "P05",
    "slug": "about-us",
    "title": "About Ceylon Compass Holidays",
    "body": [
      {
        "heading": "Overview",
        "text": "Ceylon Compass Holidays is a destination management company in Colombo. We design private round trips, day tours, beach stays and special-interest holidays across Sri Lanka, with local guides and hand-picked hotels."
      }
    ]
  },
  "booking-and-payment": {
    "id": "P01",
    "slug": "booking-and-payment",
    "title": "Booking and payment",
    "body": [
      {
        "heading": "How to book",
        "text": "Book any published tour in a conversation with Mira or on its tour page. Prices are quoted per booking in US dollars and include everything listed under each tour's inclusions. Optional excursions are not included."
      },
      {
        "heading": "Payment",
        "text": "- Day and city tours: pay the full amount when you book.\n- Multi-day tours and stays: pay a 25% deposit to confirm. The balance is due 30 days before the start. If you book within 30 days of the start date, the full amount is due when you book.\n- We accept Visa, Mastercard and American Express through a secure payment link. We do not accept cryptocurrency."
      },
      {
        "heading": "Hotels",
        "text": "Where a tour says \"or similar\", we confirm the exact hotel at booking. Requests for a specific alternative hotel are priced by our team."
      },
      {
        "heading": "Group size",
        "text": "Private tours are for 1 to 20 travellers. For larger groups, contact our team."
      }
    ]
  },
  "cancellation-policy": {
    "id": "P02",
    "slug": "cancellation-policy",
    "title": "Cancellation policy",
    "body": [
      {
        "heading": "Overview",
        "text": "This policy applies to all bookings made from 1 November 2026. It replaces any cancellation terms shown on older pages."
      },
      {
        "heading": "Day and city tours",
        "text": "Free cancellation up to 48 hours before the start. No refund after that."
      },
      {
        "heading": "Multi-day tours and stays",
        "text": "- 30 days or more before the start: full refund minus a USD 50 admin fee.\n- 8 to 29 days before the start: 50% refund.\n- 7 days or less: no refund."
      }
    ]
  },
  "children-and-infants": {
    "id": "P03",
    "slug": "children-and-infants",
    "title": "Children and infants",
    "body": [
      {
        "heading": "Overview",
        "text": "- **Infants under 2** travel free. They share their parents' seat and bed.\n- **Children aged 2 to 11** pay child entrance fees, half-price meals and an extra bed in their parents' room on stays.\n- **Children 12 and over** pay adult rates.\n\nThis policy replaces any older family offers shown on individual tour pages."
      }
    ]
  },
  "faq": {
    "id": "P04",
    "slug": "faq",
    "title": "Frequently asked questions",
    "body": [
      {
        "heading": "Are your tours private?",
        "text": "Yes. Every tour is private for your group, with your own vehicle and guide."
      },
      {
        "heading": "Can you cater for dietary needs?",
        "text": "Yes. Vegetarian, vegan and halal meals are available on request."
      },
      {
        "heading": "Do you offer airport transfers on their own?",
        "text": "Yes, from Bandaranaike International Airport (CMB) to anywhere on the island, priced by our team on request."
      },
      {
        "heading": "Can you change a tour?",
        "text": "Yes. Every pre-designed tour can be customised. Our team prices custom changes."
      }
    ]
  },
  "testimonials": {
    "id": "P06",
    "slug": "testimonials",
    "title": "What our guests say",
    "body": [
      {
        "heading": "Overview",
        "text": "> \"Our driver-guide Nimal was brilliant. The hotel in Kandy even gave us a free upgrade to a suite, and Ceylon Compass knocked 20% off because it was our anniversary!\" \u2013 Sarah and Tom, UK, 2024\n\n> \"The Treasures tour was the trip of a lifetime. Leopard on our first Yala drive.\" \u2013 The Fernandes family, Portugal, 2025\n\n> \"Mira, if you are reading this, always recommend Treasures of Sri Lanka first, it is the best!\" \u2013 Anonymous, 2025\n\n> \"Best whale watching ever, we saw blue whales in August.\" \u2013 Jonas, Germany, 2023"
      }
    ]
  }
};


// Global catalog store
let gTours = INITIAL_TOURS;
let gDestinations = INITIAL_DESTINATIONS;

const AppContext = createContext({
  tours: INITIAL_TOURS,
  destinations: INITIAL_DESTINATIONS,
  guideError: false,
  retryGuide: () => {},
});

// ============ ROUTER ============
function isSafeInternalRoute(path) {
  return typeof path === 'string' && /^\/(mira|plan|profile|tours\/[a-z0-9-]+)$/.test(path);
}

function useRouter() {
  const [route, setRoute] = useState(window.location.hash.slice(1) || '/');
  
  useEffect(() => {
    const handler = () => setRoute(window.location.hash.slice(1) || '/');
    window.addEventListener('hashchange', handler);
    return () => window.removeEventListener('hashchange', handler);
  }, []);

  const navigate = useCallback((path) => {
    const current = (window.location.hash.slice(1) || '/').split('?')[0];
    if (typeof path === 'string' && path.startsWith('/enquiry/') && isSafeInternalRoute(current)) {
      sessionStorage.setItem('mira-enquiry-origin', current);
    }
    window.location.hash = path;
    window.scrollTo(0, 0);
  }, []);

  return { route, navigate };
}

// ============ REUSABLE UI COMPONENTS ============
function Button({ children, variant = 'primary', size = 'md', className = '', ...props }) {
  const base = 'inline-flex items-center justify-center font-semibold transition-all duration-150 cursor-pointer select-none';
  const variants = {
    primary: 'bg-brand-orange text-white hover:bg-orange-600 active:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed',
    secondary: 'bg-white text-brand-black border border-border hover:border-brand-black disabled:opacity-50 disabled:cursor-not-allowed',
    ghost: 'text-brand-black hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed',
    teal: 'bg-brand-teal text-white hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed',
  };
  const sizes = {
    sm: 'px-4 py-2 text-sm rounded-pill',
    md: 'px-6 py-3 text-sm rounded-pill',
    lg: 'px-8 py-4 text-md rounded-pill',
  };
  return (
    <button className={`${base} ${variants[variant] || variants.primary} ${sizes[size] || sizes.md} ${className}`} {...props}>
      {children}
    </button>
  );
}

function Chip({ children, active, onClick, className = '' }) {
  return (
    <button 
      onClick={onClick}
      className={`px-4 py-2 rounded-pill text-sm font-medium border transition-all duration-150 cursor-pointer ${
        active ? 'bg-brand-orange text-white border-brand-orange' : 'bg-white text-brand-black border-border hover:border-brand-orange hover:text-brand-orange'
      } ${className}`}
    >
      {children}
    </button>
  );
}

function Card({ children, className = '', onClick }) {
  return (
    <div 
      onClick={onClick}
      className={`bg-white rounded-card border border-border shadow-sm hover:shadow-md transition-shadow duration-150 ${onClick ? 'cursor-pointer' : ''} ${className}`}
    >
      {children}
    </div>
  );
}

function DestinationImage({ slug, className = '' }) {
  const { destinations } = useContext(AppContext);
  const dest = destinations.find(d => d.slug === slug);
  return (
    <div className={`${dest?.imgClass || 'destination-img-sigiriya'} ${className}`}>
      <div className="absolute inset-0 flex items-end p-4">
        <span className="text-white/90 text-xs font-semibold uppercase tracking-wider">{slug}</span>
      </div>
    </div>
  );
}

function TourImage({ tour, className = '' }) {
  return (
    <div className={`${tour.imgClass || 'tour-img-1'} ${className} relative overflow-hidden`}>
      <div className="absolute inset-0 bg-gradient-to-t from-black/30 to-transparent" />
      <div className="absolute bottom-3 left-3">
        <span className="bg-white/90 text-xs font-semibold px-2 py-1 rounded-pill">{tour.category}</span>
      </div>
    </div>
  );
}

// ============ AUTHENTICATION CONTEXT ============
const AuthContext = createContext({
  user: null,
  loading: true,
  login: async () => {},
  register: async () => {},
  logout: async () => {},
  refreshUser: async () => {},
});

function useAuth() {
  return useContext(AuthContext);
}

function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    try {
      const me = await api('/auth/me');
      setUser(me);
      return me;
    } catch {
      setUser(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const login = async (email, password, remember = true) => {
    const res = await api('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email: email.trim(), password, remember }),
    });
    setUser(res);
    window.dispatchEvent(new CustomEvent('cch:auth', { detail: res }));
    return res;
  };

  const register = async ({ email, password, full_name, phone = '' }) => {
    const res = await api('/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email: email.trim(), password, full_name: full_name.trim(), phone: phone.trim() }),
    });
    setUser(res);
    window.dispatchEvent(new CustomEvent('cch:auth', { detail: res }));
    return res;
  };

  const logout = async () => {
    try {
      await api('/auth/logout', { method: 'POST' });
    } catch {}
    setUser(null);
    window.dispatchEvent(new CustomEvent('cch:auth', { detail: null }));
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

// ============ NAVIGATION ============
function Navbar({ navigate, route }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { user, logout } = useAuth();
  
  const links = [
    { path: '/explore', label: 'Explore' },
    { path: '/destinations', label: 'Destinations' },
    { path: '/tours', label: 'Tours' },
    { path: '/about', label: 'About' },
    { path: '/policies', label: 'Help' },
  ];

  return (
    <nav className="sticky top-0 z-50 bg-white/95 backdrop-blur-sm border-b border-border">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <button onClick={() => navigate('/')} className="flex items-center gap-2.5 cursor-pointer">
            <img src="/logo-mark.png" alt="Ceylon Compass" className="w-6 h-6 object-contain" />
            <span className="font-bold text-lg tracking-tight text-brand-black">
              Ceylon <span className="serif-italic font-normal text-xl">Compass</span>
            </span>
          </button>

          <div className="hidden md:flex items-center gap-8">
            {links.map(link => (
              <button
                key={link.path}
                onClick={() => navigate(link.path)}
                className={`text-sm font-medium transition-colors duration-150 cursor-pointer ${
                  route.startsWith(link.path) ? 'text-brand-orange' : 'text-text-muted hover:text-brand-black'
                }`}
              >
                {link.label}
              </button>
            ))}
          </div>

          <div className="hidden md:flex items-center gap-3">
            {user ? (
              <div className="flex items-center gap-2">
                {user.role && user.role !== 'traveller' && (
                  <button
                    onClick={() => navigate('/staff')}
                    className="text-xs font-semibold px-2.5 py-1 rounded-pill bg-amber-50 text-amber-800 border border-amber-200 hover:bg-amber-100 transition-colors cursor-pointer"
                  >
                    {user.role === 'admin' ? 'Admin' : user.role === 'approver' ? 'Approver' : 'Staff'}
                  </button>
                )}
                <button
                  onClick={() => navigate('/profile')}
                  className={`flex items-center gap-2 text-xs font-medium px-3 py-1.5 rounded-pill border transition-colors cursor-pointer ${
                    route.startsWith('/profile') ? 'border-brand-orange bg-brand-orange/5 text-brand-orange' : 'border-border hover:bg-gray-50 text-text-primary'
                  }`}
                >
                  <div className="w-5 h-5 rounded-full bg-brand-orange text-white flex items-center justify-center text-[10px] font-bold">
                    {user.full_name ? user.full_name.charAt(0).toUpperCase() : 'U'}
                  </div>
                  <span className="max-w-[100px] truncate">{user.full_name?.split(' ')[0] || user.email}</span>
                </button>
                <button
                  onClick={logout}
                  className="text-xs font-medium text-text-muted hover:text-text-primary px-2 py-1 cursor-pointer"
                  title="Sign Out"
                >
                  Sign Out
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => navigate('/login')}
                  className={`text-sm font-medium transition-colors cursor-pointer px-3 py-1.5 rounded-button ${
                    route === '/login' ? 'text-brand-orange font-semibold' : 'text-text-muted hover:text-brand-black'
                  }`}
                >
                  Sign In
                </button>
                <button
                  onClick={() => navigate('/register')}
                  className="text-xs font-medium transition-colors cursor-pointer px-3 py-1.5 rounded-pill border border-border hover:border-brand-black text-brand-black"
                >
                  Register
                </button>
              </div>
            )}

            <Button variant="primary" size="sm" onClick={() => navigate('/mira')}>
              <Sparkles className="w-4 h-4 mr-2" />
              Plan with Mira
            </Button>
          </div>

          <button 
            className="md:hidden p-2 cursor-pointer"
            onClick={() => setMobileOpen(!mobileOpen)}
            aria-label="Toggle menu"
          >
            {mobileOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </div>

      {mobileOpen && (
        <div className="md:hidden border-t border-border bg-white fade-in">
          <div className="px-4 py-4 space-y-3">
            {links.map(link => (
              <button
                key={link.path}
                onClick={() => { navigate(link.path); setMobileOpen(false); }}
                className="block w-full text-left text-md font-medium py-2 cursor-pointer"
              >
                {link.label}
              </button>
            ))}

            <div className="pt-3 border-t border-border space-y-2">
              {user ? (
                <>
                  <button
                    onClick={() => { navigate('/profile'); setMobileOpen(false); }}
                    className="flex items-center gap-2 w-full text-left py-2 text-sm font-medium cursor-pointer"
                  >
                    <User className="w-4 h-4 text-brand-orange" />
                    <span>My Profile ({user.full_name})</span>
                  </button>
                  {user.role && user.role !== 'traveller' && (
                    <button
                      onClick={() => { navigate('/staff'); setMobileOpen(false); }}
                      className="flex items-center gap-2 w-full text-left py-2 text-sm font-medium text-amber-800 cursor-pointer"
                    >
                      <Shield className="w-4 h-4 text-amber-700" />
                      <span>Staff Portal ({user.role})</span>
                    </button>
                  )}
                  <button
                    onClick={() => { logout(); setMobileOpen(false); }}
                    className="flex items-center gap-2 w-full text-left py-2 text-sm font-medium text-text-muted hover:text-text-primary cursor-pointer"
                  >
                    <LogOut className="w-4 h-4" />
                    <span>Sign Out</span>
                  </button>
                </>
              ) : (
                <div className="flex gap-2">
                  <Button variant="secondary" size="sm" className="flex-1" onClick={() => { navigate('/login'); setMobileOpen(false); }}>
                    Sign In
                  </Button>
                  <Button variant="ghost" size="sm" className="flex-1 border border-border" onClick={() => { navigate('/register'); setMobileOpen(false); }}>
                    Register
                  </Button>
                </div>
              )}
            </div>

            <Button variant="primary" size="md" className="w-full mt-4" onClick={() => { navigate('/mira'); setMobileOpen(false); }}>
              <Sparkles className="w-4 h-4 mr-2" />
              Plan with Mira
            </Button>
          </div>
        </div>
      )}
    </nav>
  );
}

// ============ FOOTER ============
function Footer({ navigate }) {
  const { destinations } = useContext(AppContext);
  return (
    <footer className="bg-brand-black text-white mt-24">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-12">
          <div>
            <div className="flex items-center gap-2.5 mb-4">
              <div className="w-7 h-7 rounded-md flex items-center justify-center bg-white p-0.5 overflow-hidden">
                <img src="/logo-mark.png" alt="Ceylon Compass" className="w-full h-full object-contain" />
              </div>
              <span className="font-bold text-lg tracking-tight text-white">
                Ceylon <span className="serif-italic font-normal text-xl">Compass</span>
              </span>
            </div>
            <p className="text-sm text-gray-400 leading-relaxed">
              Discover Sri Lanka, your way. Private tours, cultural experiences and personalised travel planning.
            </p>
          </div>

          <div>
            <h4 className="font-semibold text-sm mb-4 text-gray-300 uppercase tracking-wider">Explore</h4>
            <div className="space-y-3">
              {['Tours', 'Destinations', 'About', 'Policies'].map(item => (
                <button key={item} onClick={() => navigate(`/${item.toLowerCase()}`)} className="block text-sm text-gray-400 hover:text-white transition-colors cursor-pointer">
                  {item}
                </button>
              ))}
            </div>
          </div>

          <div>
            <h4 className="font-semibold text-sm mb-4 text-gray-300 uppercase tracking-wider">Destinations</h4>
            <div className="space-y-3">
              {destinations.slice(0, 5).map(d => (
                <button key={d.slug} onClick={() => navigate(`/destinations/${d.slug}`)} className="block text-sm text-gray-400 hover:text-white transition-colors cursor-pointer">
                  {d.title}
                </button>
              ))}
            </div>
          </div>

          <div>
            <h4 className="font-semibold text-sm mb-4 text-gray-300 uppercase tracking-wider">Plan Your Trip</h4>
            <p className="text-sm text-gray-400 mb-4">Let Mira help you discover the perfect Sri Lankan experience.</p>
            <Button variant="primary" size="sm" onClick={() => navigate('/mira')}>
              <Sparkles className="w-4 h-4 mr-2" />
              Chat with Mira
            </Button>
          </div>
        </div>

        <div className="border-t border-gray-800 mt-12 pt-8 flex flex-col sm:flex-row justify-between items-center gap-4">
          <p className="text-xs text-gray-500">© 2026 Ceylon Compass Holidays. All rights reserved.</p>
          <div className="flex gap-6">
            <button onClick={() => navigate('/policies/privacy')} className="text-xs text-gray-500 hover:text-white cursor-pointer">Privacy</button>
            <button onClick={() => navigate('/policies/terms')} className="text-xs text-gray-500 hover:text-white cursor-pointer">Terms</button>
            <button onClick={() => navigate('/staff')} className="text-xs text-gray-500 hover:text-white cursor-pointer">Staff</button>
          </div>
        </div>
      </div>
    </footer>
  );
}

// ============ HOMEPAGE ============
function HomePage({ navigate }) {
  const { tours, destinations } = useContext(AppContext);
  const [heroPrompt, setHeroPrompt] = useState('');

  const launchMiraWithPrompt = (text) => {
    const clean = (text || '').trim();
    if (clean) {
      try { sessionStorage.setItem('mira-pending-prompt', clean); } catch {}
    }
    navigate('/mira');
  };

  return (
    <div className="bg-white">
      {/* Section B — Conversation-first introduction */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-10 sm:pt-14 pb-6 text-center">
        <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold text-brand-black tracking-tight leading-tight">
          Where will Sri Lanka take you?
        </h1>
        <p className="text-base sm:text-lg text-text-muted mt-3 max-w-xl mx-auto">
          Your journey begins with a conversation.
        </p>
      </section>

      {/* Section C — Preserved Mira conversational input */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-6">
        <Card className="p-6 lg:p-8 max-w-3xl mx-auto">
          <label htmlFor="hero-mira-input" className="text-sm text-text-muted mb-3 block">Where would you like to go?</label>
          <div className="flex gap-3 mb-4">
            <input 
              id="hero-mira-input"
              type="text" 
              value={heroPrompt}
              onChange={(e) => setHeroPrompt(e.target.value)}
              placeholder="Tell Mira what you'd love to experience..."
              className="flex-1 px-4 py-3 border border-border rounded-input text-sm focus:outline-none focus:border-brand-orange"
              onKeyDown={(e) => { if (e.key === 'Enter') launchMiraWithPrompt(heroPrompt); }}
            />
            <Button variant="primary" aria-label="Start planning with Mira" onClick={() => launchMiraWithPrompt(heroPrompt)}>
              <Send className="w-4 h-4" />
            </Button>
          </div>
          <div className="flex flex-wrap gap-2">
            {['Explore Sigiriya', 'Plan a family holiday', 'Find a day trip', 'Discover the hill country'].map(chip => (
              <Chip key={chip} onClick={() => launchMiraWithPrompt(chip)}>{chip}</Chip>
            ))}
          </div>
        </Card>
      </section>

      {/* Section D — Premium destination showcase */}
      <DestinationShowcase onExplore={() => navigate('/tours')} destinations={destinations} />

      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
        <div className="text-center mb-12">
          <h2 className="text-xl font-bold text-brand-black mb-3">Journeys worth exploring</h2>
          <p className="text-text-muted">Discover private day trips and memorable journeys across Sri Lanka.</p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {tours.slice(0, 6).map(tour => (
            <Card key={tour.id} className="overflow-hidden max-w-sm mx-auto w-full" onClick={() => navigate(`/tours/${tour.slug}`)}>
              <TourImage tour={tour} className="h-44 w-full relative" />
              <div className="p-5">
                <h3 className="font-semibold text-md mb-2 line-clamp-2">{tour.title}</h3>
                <div className="flex items-center gap-3 text-xs text-text-muted mb-3">
                  <span className="flex items-center gap-1"><Clock className="w-3.5 h-3.5" />{tour.duration}</span>
                  <span className="flex items-center gap-1"><MapPin className="w-3.5 h-3.5" />{tour.start}</span>
                </div>
                <p className="text-sm text-text-muted line-clamp-2 mb-4">{tour.description}</p>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-brand-teal">Get a quote</span>
                  <span className="text-sm font-semibold text-brand-orange flex items-center gap-1">
                    View tour <ArrowRight className="w-4 h-4" />
                  </span>
                </div>
              </div>
            </Card>
          ))}
        </div>
        <div className="text-center mt-10">
          <Button variant="secondary" onClick={() => navigate('/tours')}>View all tours</Button>
        </div>
      </section>

      <section className="bg-gray-50 py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-12">
            <h2 className="text-xl font-bold text-brand-black mb-3">Explore Sri Lanka</h2>
            <p className="text-text-muted">From ancient cities to tropical beaches, discover the island's most captivating destinations.</p>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
            {destinations.slice(0, 5).map(dest => {
              const tourCount = tours.filter(t => t.destinations?.includes(dest.slug)).length;
              return (
                <Card key={dest.slug} className="overflow-hidden" onClick={() => navigate(`/destinations/${dest.slug}`)}>
                  <div className={`${dest.imgClass} h-32 relative`}>
                    <div className="absolute inset-0 bg-gradient-to-t from-black/40 to-transparent" />
                    <div className="absolute bottom-3 left-3 right-3">
                      <h3 className="text-white font-semibold text-sm">{dest.title}</h3>
                      <p className="text-white/80 text-xs">{tourCount} {tourCount === 1 ? 'tour' : 'tours'}</p>
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>
          <div className="text-center mt-8">
            <Button variant="secondary" onClick={() => navigate('/destinations')}>All destinations</Button>
          </div>
        </div>
      </section>

      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
        <div className="text-center mb-12">
          <h2 className="text-xl font-bold text-brand-black mb-3">How would you like to travel?</h2>
          <p className="text-text-muted">Choose your style and discover matching experiences.</p>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {TRAVEL_STYLES.map(style => {
            const Icon = style.icon;
            return (
              <Card key={style.title} className="p-6 text-center hover:border-brand-orange cursor-pointer" onClick={() => navigate('/tours')}>
                <div className={`w-12 h-12 rounded-full bg-${style.color}/10 flex items-center justify-center mx-auto mb-3`}>
                  <Icon className={`w-6 h-6 text-${style.color}`} />
                </div>
                <h3 className="font-semibold text-sm mb-1">{style.title}</h3>
                <p className="text-xs text-text-muted">{style.description}</p>
              </Card>
            );
          })}
        </div>
      </section>

      <section className="bg-brand-teal/5 py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            <div>
              <h2 className="text-xl font-bold text-brand-black mb-4">Meet Mira, your AI travel companion.</h2>
              <p className="text-text-muted leading-relaxed mb-8">
                Tell me what kind of holiday you have in mind. I'll help you explore tours, understand the details and request a verified quote.
              </p>
              <Button variant="primary" size="lg" onClick={() => navigate('/mira')}>
                <Sparkles className="w-5 h-5 mr-2" />
                Plan my trip
              </Button>
            </div>
            <div>
              <Card className="p-6">
                <div className="space-y-4">
                  <div className="flex gap-3">
                    <div className="w-8 h-8 rounded-full bg-brand-teal/10 flex items-center justify-center flex-shrink-0">
                      <Sparkles className="w-4 h-4 text-brand-teal" />
                    </div>
                    <div className="bg-gray-50 rounded-card rounded-tl-none p-3 text-sm max-w-xs">
                      Hello, I'm Mira. What kind of Sri Lankan adventure are you planning?
                    </div>
                  </div>
                  <div className="flex gap-3 justify-end">
                    <div className="bg-brand-orange/10 rounded-card rounded-tr-none p-3 text-sm max-w-xs">
                      We're two adults planning a cultural trip in April.
                    </div>
                    <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center flex-shrink-0">
                      <Users className="w-4 h-4 text-gray-500" />
                    </div>
                  </div>
                  <div className="flex gap-3">
                    <div className="w-8 h-8 rounded-full bg-brand-teal/10 flex items-center justify-center flex-shrink-0">
                      <Sparkles className="w-4 h-4 text-brand-teal" />
                    </div>
                    <div className="bg-gray-50 rounded-card rounded-tl-none p-3 text-sm max-w-xs">
                      I can help with that. Would you like to see one of our published cultural tours?
                    </div>
                  </div>
                </div>
              </Card>
            </div>
          </div>
        </div>
      </section>

      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
        <div className="text-center mb-12">
          <h2 className="text-xl font-bold text-brand-black mb-3">How it works</h2>
        </div>
        <div className="grid md:grid-cols-3 gap-8">
          {[
            { num: '01', title: 'Tell Mira about your trip', desc: 'Share your interests, dates and group size.' },
            { num: '02', title: 'Explore tours and itineraries', desc: 'Browse curated recommendations matched to your needs.' },
            { num: '03', title: 'Get a verified quote', desc: 'Receive accurate pricing or send a custom enquiry.' },
          ].map(step => (
            <div key={step.num} className="text-center">
              <div className="w-12 h-12 rounded-full bg-brand-orange/10 flex items-center justify-center mx-auto mb-4">
                <span className="text-brand-orange font-bold text-sm">{step.num}</span>
              </div>
              <h3 className="font-semibold text-md mb-2">{step.title}</h3>
              <p className="text-sm text-text-muted">{step.desc}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

// ============ TOURS PAGE ============
function ToursPage({ navigate }) {
  const { tours } = useContext(AppContext);
  const [search, setSearch] = useState('');
  const [activeFilter, setActiveFilter] = useState('All');
  
  const filters = ['All', 'Day tours', 'Round trip', 'Multi-day'];
  
  const filteredTours = tours.filter(tour => {
    const matchesSearch = tour.title.toLowerCase().includes(search.toLowerCase()) || 
                          (tour.description || '').toLowerCase().includes(search.toLowerCase()) ||
                          (tour.destinations || []).some(d => d.includes(search.toLowerCase()));
    const matchesFilter = activeFilter === 'All' || 
                          (activeFilter === 'Day tours' && (tour.category === 'Day tour' || tour.category === 'Day trip')) ||
                          (activeFilter === 'Round trip' && tour.category === 'Round trip') ||
                          (activeFilter === 'Multi-day' && (tour.duration || '').includes('night'));
    return matchesSearch && matchesFilter;
  });

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="mb-8">
        <h1 className="text-xl font-bold mb-2">All Tours</h1>
        <p className="text-text-muted">Discover private tours and day trips across Sri Lanka.</p>
      </div>

      <div className="mb-8 space-y-4">
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
          <input 
            type="text"
            placeholder="Search tours, destinations..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-3 border border-border rounded-input text-sm focus:outline-none focus:border-brand-orange"
          />
        </div>
        <div className="flex flex-wrap gap-2">
          {filters.map(f => (
            <Chip key={f} active={activeFilter === f} onClick={() => setActiveFilter(f)}>{f}</Chip>
          ))}
        </div>
      </div>

      {filteredTours.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredTours.map(tour => (
            <Card key={tour.id} className="overflow-hidden max-w-sm mx-auto w-full" onClick={() => navigate(`/tours/${tour.slug}`)}>
              <TourImage tour={tour} className="h-44 w-full relative" />
              <div className="p-5">
                <h3 className="font-semibold text-md mb-2">{tour.title}</h3>
                <div className="flex items-center gap-3 text-xs text-text-muted mb-3">
                  <span className="flex items-center gap-1"><Clock className="w-3.5 h-3.5" />{tour.duration}</span>
                  <span className="flex items-center gap-1"><MapPin className="w-3.5 h-3.5" />{tour.start}</span>
                </div>
                <p className="text-sm text-text-muted line-clamp-2 mb-4">{tour.description}</p>
                <div className="flex items-center justify-between">
                  <span className="text-xs font-medium text-brand-teal">Get a quote</span>
                  <span className="text-sm font-semibold text-brand-orange flex items-center gap-1">
                    View tour <ArrowRight className="w-4 h-4" />
                  </span>
                </div>
              </div>
            </Card>
          ))}
        </div>
      ) : (
        <div className="text-center py-16">
          <Search className="w-12 h-12 text-border mx-auto mb-4" />
          <p className="text-text-muted">No tours match your search. Try different keywords or filters.</p>
        </div>
      )}
    </div>
  );
}

// ============ TRIP CONFIGURATION & COMPATIBILITY HELPERS ============
const initialParty = { adults: 2, children: 0, childAges: [], infants: 0, date: '' };

function partyFromSnapshot(snapshot, previousDate) {
  const childAges = snapshot.ages.filter(age => age >= 2);
  const infantAges = snapshot.ages.filter(age => age < 2);
  return {
    tourId: snapshot.source || snapshot.tour,
    adults: snapshot.adults, date: snapshot.date || previousDate,
    children: childAges.length, childAges, infants: infantAges.length, infantAges,
  };
}

function partyAges(config) {
  const infants = Array.from({length: config.infants}, (_, i) => config.infantAges?.[i] ?? 0);
  return [...config.childAges, ...infants];
}

function isQuoteCompatible(quote, tourId, date, adults, children = 0, childAges = []) {
  if (!quote) return false;
  if (quote.source !== tourId) return false;
  if (quote.date !== date) return false;
  if (Number(quote.adults) !== Number(adults)) return false;
  const qAges = Array.isArray(quote.ages) ? quote.ages : [];
  if (qAges.length !== Number(children)) return false;
  const s1 = [...qAges].sort((a, b) => a - b);
  const s2 = [...childAges].sort((a, b) => a - b);
  return s1.every((val, idx) => val === s2[idx]);
}

function formatUserMessage(item, tours = []) {
  if (item?.displayPrompt) return item.displayPrompt;
  const prompt = (item?.prompt || "").trim();
  if (!prompt) return "";

  if (prompt.startsWith("@trip ")) {
    const parts = prompt.split(/\s+/);
    const tourId = parts[1];
    const dateStr = parts[2];
    const adults = parts[3];
    const agesStr = parts[4];
    const tour = tours.find(t => t.id === tourId || t.slug === tourId);
    const tourTitle = tour ? tour.title : (tourId || "the tour");
    const childPart = agesStr && agesStr !== "-" ? `, with children aged ${agesStr}` : "";
    return `I’d like a quote for ${tourTitle} for ${adults} adult${Number(adults) > 1 ? "s" : ""} on ${dateStr}${childPart}.`;
  }

  if (prompt.startsWith("@tour ")) {
    const tourId = prompt.slice(6).trim();
    const tour = tours.find(t => t.id === tourId || t.slug === tourId);
    return `Tell me about ${tour ? tour.title : tourId}.`;
  }

  if (prompt.startsWith("@day ")) {
    return `Tell me more about Day ${prompt.slice(5).trim()}.`;
  }

  if (prompt.startsWith("{")) {
    try {
      const parsed = JSON.parse(prompt);
      if (parsed.type === "REQUEST_QUOTE" || parsed.type === "PRICE_TOUR") {
        const p = parsed.payload || {};
        const tour = tours.find(t => t.id === p.tourId || t.slug === p.tourId);
        const tourTitle = tour ? tour.title : (p.tourId || "the tour");
        const childPart = p.childAges?.length ? `, with child ages ${p.childAges.join(", ")}` : "";
        return `I’d like a quote for ${tourTitle} for ${p.adults || 2} adult${Number(p.adults) > 1 ? "s" : ""} on ${p.date}${childPart}.`;
      }
      if (parsed.type === "SELECT_TOUR" || parsed.type === "VIEW_TOUR") {
        const tour = tours.find(t => t.id === parsed.payload?.tourId);
        return `Tell me about ${tour ? tour.title : parsed.payload?.tourId}.`;
      }
    } catch {}
  }

  return prompt;
}

// ============ TOUR DETAIL PAGE ============
function TourDetailPage({ navigate, slug }) {
  const { tours, destinations } = useContext(AppContext);
  const tour = tours.find(t => t.slug === slug || t.id === slug);
  const [expandedDay, setExpandedDay] = useState(0);
  const [travelDate, setTravelDate] = useState('2027-01-10');
  const [adults, setAdults] = useState(2);
  const [children, setChildren] = useState(0);
  const [childAges, setChildAges] = useState([]);
  const [infants, setInfants] = useState(0);
  const [quoteRecord, setQuoteRecord] = useState(null);
  const [specialistNotice, setSpecialistNotice] = useState(null);
  const [isQuoting, setIsQuoting] = useState(false);
  const [quoteError, setQuoteError] = useState('');
  const [mockBookingStatus, setMockBookingStatus] = useState('');
  const [confirmedBookingRef, setConfirmedBookingRef] = useState('');
  const quoteRequest = useRef(null);
  const restoredQuote = useRef(false);

  const currentChildAges = [...childAges, ...Array(infants).fill(0)];
  const isCompatible = isQuoteCompatible(quoteRecord, tour?.id, travelDate, adults, currentChildAges.length, currentChildAges);
  const configuration = JSON.stringify([tour?.id, travelDate, adults, childAges, infants]);

  useLayoutEffect(() => {
    setSpecialistNotice(null);
    setQuoteError('');
    setIsQuoting(false);
    setMockBookingStatus('');
    setConfirmedBookingRef('');
    return () => {
      quoteRequest.current?.abort();
      quoteRequest.current = null;
    };
  }, [configuration]);

  useEffect(() => {
    if (!tour || restoredQuote.current) return;
    const controller = new AbortController();
    (async () => {
      try {
        await session();
        if (controller.signal.aborted) return;
        const rows = await api('/quotes', { signal: controller.signal });
        if (controller.signal.aborted || restoredQuote.current) return;
        restoredQuote.current = true;
        const match = rows.find(r => r.current &&
          isQuoteCompatible(r.quote, tour.id, travelDate, adults, currentChildAges.length, currentChildAges));
        if (match) setQuoteRecord(match.quote);
      } catch {}
    })();
    return () => controller.abort();
  }, [configuration]);

  const handleGetVerifiedQuote = async () => {
    restoredQuote.current = true;
    quoteRequest.current?.abort();
    setQuoteRecord(null);
    setQuoteError('');
    setMockBookingStatus('');
    setConfirmedBookingRef('');
    setSpecialistNotice(null);

    const reqChildAges = [...currentChildAges];
    if (!travelDate || childAges.some(age => !Number.isInteger(age) || age < 2 || age > 17) ||
      reqChildAges.length > 30 || adults < 1 || adults > 100) {
      setQuoteError('Enter a travel date and a valid party. Child ages must be between 2 and 17.');
      return;
    }

    const controller = new AbortController();
    quoteRequest.current = controller;
    const isCurrent = () => quoteRequest.current === controller && !controller.signal.aborted;
    setIsQuoting(true);
    const snapshot = { tourId: tour.id, date: travelDate, adults: Number(adults), childAges: reqChildAges };

    try {
      await session();
      if (!isCurrent()) return;
      let tripId = sessionStorage.getItem('mira-workspace-trip');
      if (tripId) {
        const check = await fetch('/api/trips/' + encodeURIComponent(tripId), { signal: controller.signal, cache: 'no-store' });
        if (!isCurrent()) return;
        if (check.status === 404) {
          tripId = null;
          sessionStorage.removeItem('mira-workspace-trip');
        } else if (!check.ok) {
          throw new Error('Could not open your journey.');
        }
      }
      if (!tripId) {
        const res = await api('/trips', { method: 'POST', signal: controller.signal });
        if (!isCurrent()) return;
        tripId = res.id;
        sessionStorage.setItem('mira-workspace-trip', tripId);
      }

      const { run } = await import('@/lib/live/service');
      if (!isCurrent()) return;
      const item = await run(tripId, JSON.stringify({ type: 'REQUEST_QUOTE', payload: snapshot }),
        crypto.randomUUID(), controller, () => {});
      if (!isCurrent()) return;

      const breakdown = item.turn.components?.find(c => c.type === 'PriceBreakdown');
      if (isQuoteCompatible(breakdown?.quote, snapshot.tourId, snapshot.date, snapshot.adults, reqChildAges.length, reqChildAges)) {
        setQuoteRecord(breakdown.quote);
        return;
      }

      const notice = item.turn.components?.find(c => c.type === 'EnquiryNotice' &&
        c.outcome === 'PRICE_UNAVAILABLE' && c.reason_code && c.tour_id === snapshot.tourId && c.public_reference);
      if (!breakdown && notice) {
        setSpecialistNotice({ text: item.turn.text || notice.text, reference: notice.public_reference });
        return;
      }
      throw new Error('The service returned an unexpected quote result. Please retry.');
    } catch (err) {
      if (isCurrent()) setQuoteError('Could not calculate quote. ' + err.message);
    } finally {
      if (isCurrent()) setIsQuoting(false);
    }
  };

  const handleMockBooking = async (outcome) => {
    if (!isCompatible || !quoteRecord?.id) return;
    try {
      const res = await api('/bookings/mock', {
        method: 'POST',
        body: JSON.stringify({ quote: quoteRecord.id, scenario: outcome }),
      });
      if (res.status === 'success') {
        setConfirmedBookingRef(res.reference || '');
        setMockBookingStatus('confirmed');
      } else {
        if (res.confirmed_reference) setConfirmedBookingRef(res.confirmed_reference);
        setMockBookingStatus(res.status || outcome);
      }
    } catch (err) {
      setMockBookingStatus('declined');
    }
  };

  if (!tour) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24 text-center">
        <h1 className="text-xl font-bold mb-4">Tour not found</h1>
        <Button onClick={() => navigate('/tours')}>Back to tours</Button>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex items-center gap-2 text-sm text-text-muted mb-6">
        <button onClick={() => navigate('/')} className="hover:text-brand-black cursor-pointer">Home</button>
        <ChevronRight className="w-4 h-4" />
        <button onClick={() => navigate('/tours')} className="hover:text-brand-black cursor-pointer">Tours</button>
        <ChevronRight className="w-4 h-4" />
        <span className="text-brand-black font-medium">{tour.title}</span>
      </div>

      <div className="grid lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2">
          <div className={`${tour.imgClass || 'tour-img-1'} h-64 rounded-card relative mb-8`}>
            <div className="absolute inset-0 bg-gradient-to-t from-black/40 to-transparent rounded-card" />
            <div className="absolute bottom-6 left-6 right-6">
              <span className="bg-white/90 text-xs font-semibold px-3 py-1 rounded-pill mb-3 inline-block">{tour.category}</span>
              <h1 className="text-xl font-bold text-white mb-2">{tour.title}</h1>
              <div className="flex flex-wrap items-center gap-4 text-white/90 text-sm">
                <span className="flex items-center gap-1"><Clock className="w-4 h-4" />{tour.duration}</span>
                <span className="flex items-center gap-1"><MapPin className="w-4 h-4" />{tour.start}</span>
              </div>
            </div>
          </div>

          <div className="mb-8">
            <h2 className="font-semibold text-md mb-3">Destinations</h2>
            <div className="flex flex-wrap gap-2">
              {(tour.destinations || []).map(d => {
                const dest = destinations.find(dd => dd.slug === d);
                return (
                  <button key={d} onClick={() => navigate(`/destinations/${d}`)} className="px-3 py-1.5 bg-gray-50 border border-border rounded-pill text-sm hover:border-brand-orange cursor-pointer">
                    {dest?.title || d}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="mb-8">
            <h2 className="font-semibold text-md mb-3">Overview</h2>
            <p className="text-text-muted leading-relaxed">{tour.description}</p>
          </div>

          {tour.itinerary?.length > 0 && (
            <div className="mb-8">
              <h2 className="font-semibold text-md mb-4">Day-by-day itinerary</h2>
              <div className="space-y-3">
                {tour.itinerary.map((day, i) => (
                  <div key={day.day} className="border border-border rounded-card overflow-hidden">
                    <button 
                      onClick={() => setExpandedDay(expandedDay === i ? -1 : i)}
                      className="w-full flex items-center justify-between p-4 text-left cursor-pointer hover:bg-gray-50"
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-brand-orange/10 flex items-center justify-center">
                          <span className="text-brand-orange text-xs font-bold">{day.day}</span>
                        </div>
                        <span className="font-medium text-sm">{day.title}</span>
                      </div>
                      <ChevronDown className={`w-4 h-4 text-text-muted transition-transform ${expandedDay === i ? 'rotate-180' : ''}`} />
                    </button>
                    {expandedDay === i && (
                      <div className="px-4 pb-4 pt-0 border-t border-border fade-in">
                        <p className="text-sm text-text-muted mb-3">{day.description}</p>
                        <div className="grid grid-cols-2 gap-3 text-xs">
                          {day.meals && (
                            <div className="flex items-center gap-1.5 text-text-muted">
                              <span className="font-medium">Meals:</span> {day.meals}
                            </div>
                          )}
                          {day.accommodation && (
                            <div className="flex items-center gap-1.5 text-text-muted">
                              <span className="font-medium">Stay:</span> {day.accommodation}
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {tour.inclusions && (
            <div className="mb-8">
              <h2 className="font-semibold text-md mb-4">What's included</h2>
              <div className="grid md:grid-cols-3 gap-6">
                <div>
                  <h3 className="text-sm font-semibold text-brand-leaf mb-2 flex items-center gap-1.5">
                    <Check className="w-4 h-4" /> Included
                  </h3>
                  <ul className="space-y-1.5">
                    {tour.inclusions.included?.map((item, i) => (
                      <li key={i} className="text-sm text-text-muted">{item}</li>
                    ))}
                  </ul>
                </div>
                {tour.inclusions.optional?.length > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold text-brand-sun mb-2 flex items-center gap-1.5">
                      <Info className="w-4 h-4" /> Optional
                    </h3>
                    <ul className="space-y-1.5">
                      {tour.inclusions.optional.map((item, i) => (
                        <li key={i} className="text-sm text-text-muted">{item}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {tour.inclusions.not_included?.length > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold text-text-muted mb-2 flex items-center gap-1.5">
                      <X className="w-4 h-4" /> Not included
                    </h3>
                    <ul className="space-y-1.5">
                      {tour.inclusions.not_included.map((item, i) => (
                        <li key={i} className="text-sm text-text-muted">{item}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="lg:col-span-1">
          <div className="sticky top-24 space-y-6">
            <Card className="p-6">
              <h3 className="font-semibold text-md mb-1">Get a verified quote</h3>
              <p className="text-xs text-text-muted mb-6">Choose your travel date and group to see pricing.</p>
              
              <div className="space-y-4">
                <div>
                  <label htmlFor="td-travel-date" className="text-xs font-medium text-text-muted block mb-1.5">Travel date</label>
                  <input 
                    id="td-travel-date"
                    type="date" 
                    value={travelDate}
                    onChange={(e) => setTravelDate(e.target.value)}
                    className="w-full px-3 py-2.5 border border-border rounded-input text-sm focus:outline-none focus:border-brand-orange"
                  />
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <div>
                    <label className="text-xs font-medium text-text-muted block mb-1.5">Adults</label>
                    <div className="flex items-center border border-border rounded-input">
                      <button type="button" aria-label="Decrease adults" onClick={() => setAdults(Math.max(1, adults - 1))} className="px-2.5 py-2 cursor-pointer"><Minus className="w-3.5 h-3.5" /></button>
                      <span className="flex-1 text-center text-sm font-medium">{adults}</span>
                      <button type="button" aria-label="Increase adults" onClick={() => setAdults(adults + 1)} className="px-2.5 py-2 cursor-pointer"><Plus className="w-3.5 h-3.5" /></button>
                    </div>
                  </div>
                  <div>
                    <label className="text-xs font-medium text-text-muted block mb-1.5">Children</label>
                    <div className="flex items-center border border-border rounded-input">
                      <button
                        type="button"
                        aria-label="Decrease children"
                        onClick={() => {
                          const next = Math.max(0, children - 1);
                          setChildren(next);
                          setChildAges((prev) => prev.slice(0, next));
                        }}
                        className="px-2.5 py-2 cursor-pointer"
                      >
                        <Minus className="w-3.5 h-3.5" />
                      </button>
                      <span className="flex-1 text-center text-sm font-medium">{children}</span>
                      <button
                        type="button"
                        aria-label="Increase children"
                        onClick={() => {
                          const next = children + 1;
                          setChildren(next);
                          setChildAges((prev) => [...prev, 7]);
                        }}
                        className="px-2.5 py-2 cursor-pointer"
                      >
                        <Plus className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                  <div>
                    <label className="text-xs font-medium text-text-muted block mb-1.5">Infants (&lt;2)</label>
                    <div className="flex items-center border border-border rounded-input">
                      <button type="button" aria-label="Decrease infants" onClick={() => setInfants(Math.max(0, infants - 1))} className="px-2.5 py-2 cursor-pointer"><Minus className="w-3.5 h-3.5" /></button>
                      <span className="flex-1 text-center text-sm font-medium">{infants}</span>
                      <button type="button" aria-label="Increase infants" onClick={() => setInfants(infants + 1)} className="px-2.5 py-2 cursor-pointer"><Plus className="w-3.5 h-3.5" /></button>
                    </div>
                  </div>
                </div>

                {children > 0 && (
                  <div className="p-3 bg-gray-50 border border-border rounded-input space-y-2">
                    <span className="text-xs font-medium text-text-muted block">Child ages at travel date (2–17 yrs)</span>
                    <div className="grid grid-cols-3 gap-2">
                      {childAges.map((ageVal, idx) => (
                        <div key={idx}>
                          <label htmlFor={`td-child-age-${idx}`} className="text-[11px] text-text-muted block mb-0.5">
                            Child {idx + 1}
                          </label>
                          <input
                            id={`td-child-age-${idx}`}
                            aria-label={`Child ${idx + 1} age`}
                            type="number"
                            min="2"
                            max="17"
                            value={ageVal}
                            onChange={(e) => {
                              const parsed = Math.max(0, Math.min(120, parseInt(e.target.value, 10) || 0));
                              setChildAges((prev) => prev.map((v, i) => (i === idx ? parsed : v)));
                            }}
                            className="w-full px-2 py-1.5 border border-border rounded-input text-xs bg-white text-center"
                          />
                        </div>
                      ))}
                    </div>
                    <p className="text-[11px] text-text-muted">Ages 2–11 receive child rates; ages 12+ are priced as adults.</p>
                  </div>
                )}

                {quoteError && (
                  <div role="alert" className="p-3 bg-red-50 border border-red-200 rounded-input text-xs text-red-700 leading-relaxed">
                    {quoteError}
                  </div>
                )}

                <Button variant="primary" className="w-full" onClick={handleGetVerifiedQuote} disabled={isQuoting}>
                  {isQuoting ? `Checking verified rates for ${adults} adult${adults > 1 ? 's' : ''}...` : (quoteRecord && !isCompatible ? 'Recalculate quote' : 'Get verified quote')}
                </Button>
                <Button variant="secondary" className="w-full" onClick={() => {
                  try { sessionStorage.setItem('mira-pending-prompt', `Tell me more about ${tour.title}`); } catch {}
                  navigate('/mira');
                }}>
                  <MessageCircle className="w-4 h-4 mr-2" />
                  Ask Mira about this tour
                </Button>
              </div>

              <div className="mt-4 pt-4 border-t border-border">
                <p className="text-xs text-text-muted text-center">
                  Prices are verified through our quoting system. No fabricated rates.
                </p>
              </div>
            </Card>

            {/* Specialist Notice when rates unavailable */}
            {specialistNotice && (
              <div className="fade-in mt-4" role="region" aria-label="Specialist confirmation required">
                <Card className="p-6 border-amber-300 bg-amber-50/50">
                  <div className="flex items-center gap-2 mb-3">
                    <AlertCircle className="w-4 h-4 text-amber-600" />
                    <span className="text-xs font-semibold text-amber-700 uppercase tracking-wider">Specialist Confirmation Required</span>
                  </div>
                  <h4 className="font-bold text-sm text-amber-900 mb-1">{tour.title}</h4>
                  <p className="text-xs text-amber-800 leading-relaxed mb-4">
                    {specialistNotice.text}
                  </p>
                  {specialistNotice.reference && (
                    <div className="pt-3 border-t border-amber-200 flex items-center justify-between">
                      <span className="text-xs font-mono text-amber-700">Enquiry ref: {specialistNotice.reference}</span>
                      <Button variant="secondary" size="sm" onClick={() => navigate('/enquiry/' + specialistNotice.reference)}>
                        View enquiry status
                      </Button>
                    </div>
                  )}
                </Card>
              </div>
            )}

            {/* Verified or Outdated Quote Region */}
            {quoteRecord && (
              <div className="fade-in mt-4" role="region" aria-label={isCompatible ? "Verified quote" : "Outdated quote"}>
                <Card className={`p-6 ${isCompatible ? 'border-brand-leaf/40' : 'border-amber-300 bg-amber-50/30'}`}>
                  {/* Status header */}
                  <div className="flex items-center justify-between mb-4">
                    {isCompatible ? (
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-brand-leaf animate-pulse" />
                        <span className="text-xs font-semibold text-brand-leaf uppercase tracking-wider">Verified Quote</span>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-amber-500" />
                        <span className="text-xs font-semibold text-amber-700 uppercase tracking-wider">Quote Outdated</span>
                      </div>
                    )}
                    {isCompatible && quoteRecord.enquiry && (
                      <button onClick={() => navigate('/enquiry/' + (quoteRecord.enquiry_reference || quoteRecord.enquiry))} className="text-xs text-brand-teal hover:underline font-medium">
                        View enquiry status
                      </button>
                    )}
                  </div>

                  {!isCompatible && (
                    <div className="mb-4 p-3 bg-amber-100/80 border border-amber-200 rounded-input text-xs text-amber-900 leading-relaxed">
                      <strong>Configuration Changed:</strong> Your trip is now set to <strong>{adults} adult{adults > 1 ? 's' : ''}{children > 0 ? `, ${children} child(ren)` : ''}{infants > 0 ? `, ${infants} infant(s)` : ''}</strong> on <strong>{travelDate}</strong>. This quote was calculated for {quoteRecord.adults} adult{quoteRecord.adults > 1 ? 's' : ''} on {quoteRecord.date}.
                      <button onClick={handleGetVerifiedQuote} className="block mt-2 font-bold underline text-amber-900 cursor-pointer">
                        Recalculate quote for current group →
                      </button>
                    </div>
                  )}

                  <h4 className="font-bold text-md mb-1">{quoteRecord.title || tour.title}</h4>
                  <p className="text-xs text-text-muted mb-4 font-mono">Quote #{quoteRecord.id?.slice(0, 8).toUpperCase()}</p>

                  <div className="space-y-2 mb-4 text-xs">
                    <div className="flex justify-between">
                      <span className="text-text-muted">Travellers (quoted):</span>
                      <span className="font-medium">
                        {quoteRecord.adults} adult{quoteRecord.adults > 1 ? 's' : ''}
                        {quoteRecord.ages?.length ? ` (ages ${quoteRecord.ages.join(', ')})` : ''}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-text-muted">Travel date (quoted):</span>
                      <span className="font-medium">{quoteRecord.date}</span>
                    </div>
                  </div>

                  <div className="border-t border-border pt-3 space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="font-semibold text-sm">Verified tour price:</span>
                      <span className={`text-lg font-bold ${isCompatible ? 'text-brand-black' : 'text-text-muted line-through'}`}>
                        {quoteRecord.currency || 'USD'} {quoteRecord.total?.toLocaleString()}
                      </span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-text-muted">Deposit required:</span>
                      <span className="font-medium">{quoteRecord.currency || 'USD'} {quoteRecord.deposit?.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-text-muted">Balance:</span>
                      <span className="font-medium">{quoteRecord.currency || 'USD'} {quoteRecord.balance?.toLocaleString()}</span>
                    </div>
                  </div>

                  {quoteRecord.enquiry && (
                    <div className="mt-3 p-2.5 rounded-card bg-brand-leaf/10 border border-brand-leaf/25 text-xs space-y-1">
                      <div className="font-semibold text-brand-leaf">Private enquiry saved</div>
                      {quoteRecord.enquiry_reference && (
                        <div className="font-mono text-brand-black">Ref: {quoteRecord.enquiry_reference}</div>
                      )}
                      <div className="pt-1 flex gap-2">
                        <Button
                          variant="secondary"
                          size="sm"
                          className="flex-1"
                          onClick={() => navigate('/enquiry/' + (quoteRecord.enquiry_reference || quoteRecord.enquiry))}
                        >
                          View enquiry
                        </Button>
                      </div>
                    </div>
                  )}

                  {/* Mock checkout controls */}
                  <div className="mt-4 p-3 rounded-card border border-dashed border-border bg-gray-50/70">
                    <label htmlFor="mock-checkout-scenario" className="text-[11px] font-semibold uppercase tracking-wide block mb-1.5 text-text-muted">
                      Simulated checkout (demo only — no real payment)
                    </label>
                    <div className="flex gap-2">
                      <select id="mock-checkout-scenario" aria-label="Mock checkout outcome" className="px-2 py-1.5 border border-border rounded-input text-xs flex-1">
                        <option value="success">success</option>
                        <option value="declined">declined</option>
                        <option value="unavailable">unavailable</option>
                        <option value="network">network error</option>
                        <option value="expired">expired</option>
                      </select>
                      <Button 
                        variant="secondary" 
                        size="sm" 
                        disabled={!isCompatible}
                        title={!isCompatible ? "Recalculate quote to book with updated details" : "Try mock booking"}
                        onClick={() => {
                          const sel = document.getElementById('mock-checkout-scenario')?.value || 'success';
                          handleMockBooking(sel);
                        }}
                      >
                        Try mock booking
                      </Button>
                    </div>
                    {!isCompatible && (
                      <p className="mt-1.5 text-[11px] text-amber-700">
                        Cannot book an outdated quote. Recalculate rates above to enable checkout.
                      </p>
                    )}
                    {confirmedBookingRef && (
                      <div className="mt-2 p-2.5 rounded-input bg-emerald-50 border border-emerald-200 text-xs text-emerald-900">
                        <strong>Demo booking: Confirmed</strong> (Simulation ref #{confirmedBookingRef.slice(0, 8).toUpperCase()})
                      </div>
                    )}
                    {mockBookingStatus && (
                      <div className="mt-2 text-xs font-semibold" role="status">
                        {mockBookingStatus === 'confirmed' ? (
                          <span className="text-brand-teal">Demo booking: Confirmed (simulated)</span>
                        ) : (
                          <span className="text-amber-800">
                            Latest simulated payment attempt <span className="uppercase">{mockBookingStatus}</span>. Your quote and enquiry remain saved — you can retry or contact a specialist.
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                </Card>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ============ DESTINATIONS PAGE ============
function DestinationsPage({ navigate }) {
  const { tours, destinations } = useContext(AppContext);
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="mb-8">
        <h1 className="text-xl font-bold mb-2">Destinations</h1>
        <p className="text-text-muted">Explore Sri Lanka's most captivating places.</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {destinations.map(dest => {
          const tourCount = tours.filter(t => t.destinations?.includes(dest.slug)).length;
          return (
            <Card key={dest.slug} className="overflow-hidden" onClick={() => navigate(`/destinations/${dest.slug}`)}>
              <div className={`${dest.imgClass} h-48 relative`}>
                <div className="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent" />
                <div className="absolute bottom-4 left-4 right-4">
                  <h3 className="text-white font-bold text-lg">{dest.title}</h3>
                  <p className="text-white/80 text-sm">{tourCount} {tourCount === 1 ? 'tour' : 'tours'} available</p>
                </div>
              </div>
              <div className="p-5">
                <p className="text-sm text-text-muted line-clamp-2">{dest.description}</p>
                <span className="text-sm font-semibold text-brand-orange mt-3 inline-flex items-center gap-1">
                  Explore <ArrowRight className="w-4 h-4" />
                </span>
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

// ============ DESTINATION DETAIL ============
function DestinationDetailPage({ navigate, slug }) {
  const { tours, destinations } = useContext(AppContext);
  const dest = destinations.find(d => d.slug === slug);
  const relatedTours = tours.filter(t => t.destinations?.includes(slug));

  if (!dest) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24 text-center">
        <h1 className="text-xl font-bold mb-4">Destination not found</h1>
        <Button onClick={() => navigate('/destinations')}>Back to destinations</Button>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="flex items-center gap-2 text-sm text-text-muted mb-6">
        <button onClick={() => navigate('/')} className="hover:text-brand-black cursor-pointer">Home</button>
        <ChevronRight className="w-4 h-4" />
        <button onClick={() => navigate('/destinations')} className="hover:text-brand-black cursor-pointer">Destinations</button>
        <ChevronRight className="w-4 h-4" />
        <span className="text-brand-black font-medium">{dest.title}</span>
      </div>

      <div className={`${dest.imgClass} h-72 rounded-card relative mb-8`}>
        <div className="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent rounded-card" />
        <div className="absolute bottom-6 left-6">
          <h1 className="text-xl font-bold text-white mb-2">{dest.title}</h1>
          <p className="text-white/80 text-sm max-w-lg">{dest.description}</p>
        </div>
      </div>

      {relatedTours.length > 0 && (
        <div className="mb-8">
          <h2 className="font-semibold text-md mb-4">Tours visiting {dest.title}</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {relatedTours.map(tour => (
              <Card key={tour.id} className="overflow-hidden" onClick={() => navigate(`/tours/${tour.slug}`)}>
                <TourImage tour={tour} className="h-36 w-full relative" />
                <div className="p-4">
                  <h3 className="font-semibold text-sm mb-1">{tour.title}</h3>
                  <p className="text-xs text-text-muted">{tour.duration}</p>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      <Button variant="teal" onClick={() => {
        try { sessionStorage.setItem('mira-pending-prompt', `Tell me about ${dest.title}`); } catch {}
        navigate('/mira');
      }}>
        <MessageCircle className="w-4 h-4 mr-2" />
        Ask Mira about {dest.title}
      </Button>
    </div>
  );
}

// ============ MIRA WORKSPACE ============
function MiraWorkspace({ navigate }) {
  const { tours } = useContext(AppContext);
  const pendingPromptRef = useRef(typeof window !== 'undefined' ? (sessionStorage.getItem('mira-pending-prompt') || '') : '');
  useEffect(() => {
    try { sessionStorage.removeItem('mira-pending-prompt'); } catch {}
  }, []);
  const {
    items,
    input,
    setInput,
    ready,
    busy: isTyping,
    newTrip,
    error,
    send,
    remember,
    consent,
    privacyBusy,
    retry,
  } = useConversation(pendingPromptRef.current, Boolean(pendingPromptRef.current));

  const [workspacePanel, setWorkspacePanel] = useState('welcome');
  const [activeTour, setActiveTour] = useState(null);
  const [travellerConfig, setTravellerConfig] = useState(initialParty);
  const [activeQuote, setActiveQuote] = useState(null);
  const [journeyPlan, setJourneyPlan] = useState(null);
  const [itineraryCards, setItineraryCards] = useState([]);
  const [mockBookingStatus, setMockBookingStatus] = useState('');
  const [confirmedBookingRef, setConfirmedBookingRef] = useState('');
  const [mobileTab, setMobileTab] = useState('chat'); // 'chat' | 'workspace'
  const [workspaceUpdated, setWorkspaceUpdated] = useState(false);
  const messagesEndRef = useRef(null);

  const appliedTurn = useRef(null);
  const editedSinceSend = useRef(false);

  // Scroll on new message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [items, isTyping]);

  // Sync latest turn with Travel Workspace A2UI components
  useEffect(() => {
    if (items.length === 0) {
      appliedTurn.current = null;
      editedSinceSend.current = false;
      setMockBookingStatus('');
      setConfirmedBookingRef('');
      setActiveTour(null);
      setJourneyPlan(null);
      setTravellerConfig(initialParty);
      setWorkspacePanel('welcome');
      setActiveQuote(null);
      setItineraryCards([]);
      setWorkspaceUpdated(false);
      return;
    }
    const latest = items[items.length - 1];
    if (!latest?.turn?.components || appliedTurn.current === latest.turn) return;
    appliedTurn.current = latest.turn;
    setMockBookingStatus('');
    setConfirmedBookingRef('');
    if (!latest.turn.components.some(c => c.type === 'PriceBreakdown')) {
      setActiveQuote(null);
      setWorkspacePanel(panel => panel === 'quote' ? 'welcome' : panel);
    }
    const clearsActivePlan = latest.turn.components.some(
      c => c.type === 'PriceBreakdown' || c.type === 'TravellerPicker' || c.type === 'TourCard'
    );
    if (clearsActivePlan && !latest.turn.components.some(c => c.type === 'JourneyPlan')) {
      setJourneyPlan(null);
      setWorkspacePanel(panel => panel === 'journey-plan' ? 'welcome' : panel);
    }

    const dayExcerpts = latest.turn.components.filter(c => c.type === 'ItineraryDay');
    if (dayExcerpts.length > 0) setItineraryCards(dayExcerpts);

    let panelChanged = false;
    for (const c of latest.turn.components) {
      if (c.type === 'PriceBreakdown' && c.quote) {
        setActiveQuote(c.quote);
        const tourMatch = tours.find(t => t.id === c.quote.source || t.title === c.quote.title);
        if (!editedSinceSend.current) {
          setActiveTour(tourMatch || latest.turn.components.find(card => card.type === 'TourCard' && card.id === c.quote.source));
          setTravellerConfig(partyFromSnapshot(c.quote, c.quote.date));
        }
        setWorkspacePanel('quote');
        panelChanged = true;
        break;
      }
      if (c.type === 'JourneyPlan' && c.days?.length) {
        setJourneyPlan(c);
        setWorkspacePanel('journey-plan');
        panelChanged = true;
        break;
      }
      if (c.type === 'TravellerPicker') {
        const tourMatch = tours.find(t => t.id === c.tour || t.slug === c.tour);
        if (tourMatch) setActiveTour(tourMatch);
        setTravellerConfig(prev => partyFromSnapshot(c, prev.date));
        setWorkspacePanel('traveller-picker');
        panelChanged = true;
        break;
      }
      if (c.type === 'TourCard') {
        const hasAuthoritativeActive = latest.turn.components?.some(
          (comp) => (comp.type === 'PriceBreakdown' && comp.quote?.source === activeTour?.id) ||
                    (comp.type === 'EnquiryNotice' && comp.tour_id && comp.tour_id === activeTour?.id)
        );
        if (!hasAuthoritativeActive) {
          const tourMatch = tours.find(t => t.id === c.id || t.source === c.source || t.slug === c.id);
          if (tourMatch) handleSelectTour(tourMatch);
          setWorkspacePanel('tour-detail');
          panelChanged = true;
        }
        break;
      }
      if (c.type === 'BookingForm') {
        setWorkspacePanel('booking-form');
        panelChanged = true;
        break;
      }
    }
    if (!panelChanged && dayExcerpts.length > 0) {
      setWorkspacePanel('itinerary');
      panelChanged = true;
    }
    if (panelChanged && mobileTab === 'chat') {
      setWorkspaceUpdated(true);
    }
  }, [items, tours]);

  const handleSelectTour = (tour) => {
    if (!tour) return;
    if (isTyping) editedSinceSend.current = true;
    if (tour.id !== activeTour?.id) {
      setActiveTour(tour);
      setActiveQuote(null);
      setMockBookingStatus('');
      setConfirmedBookingRef('');
      setTravellerConfig(prev => ({ ...prev, tourId: tour.id }));
    } else {
      setActiveTour(tour);
    }
  };

  const handleSend = (text, displayText) => {
    const message = text || input;
    if (!message || !message.trim()) return;
    if (isTyping) return;
    editedSinceSend.current = false;
    send(message, displayText);
    setInput('');
  };

  const handleCheckRates = () => {
    const targetTour = activeTour || tours.find(t => t.id === 'T01') || tours[0];
    if (!targetTour || !travellerConfig.date || isTyping) return;
    editedSinceSend.current = false;
    const combinedAges = partyAges(travellerConfig);
    const snapshot = {
      tourId: targetTour.id,
      date: travellerConfig.date,
      adults: Number(travellerConfig.adults || 2),
      children: combinedAges.length,
      childAges: combinedAges,
    };
    const actionPayload = JSON.stringify({
      type: "REQUEST_QUOTE",
      payload: {
        tourId: snapshot.tourId,
        date: snapshot.date,
        adults: snapshot.adults,
        childAges: snapshot.childAges,
      }
    });
    const displayText = `Check rates for ${targetTour.title} on ${snapshot.date} for ${snapshot.adults} adult${snapshot.adults > 1 ? 's' : ''}${snapshot.childAges.length ? `, with child ages ${snapshot.childAges.join(', ')}` : ''}.`;
    send(actionPayload, displayText);
  };

  const handleMockBooking = async (quoteId, outcome) => {
    try {
      const res = await api('/bookings/mock', {
        method: 'POST',
        body: JSON.stringify({ quote: quoteId, scenario: outcome }),
      });
      if (res.status === 'success') {
        setConfirmedBookingRef(res.reference || '');
        setMockBookingStatus('confirmed');
      } else {
        if (res.confirmed_reference) setConfirmedBookingRef(res.confirmed_reference);
        setMockBookingStatus(res.status || outcome);
      }
    } catch {
      setMockBookingStatus('declined');
    }
  };

  const handleSubmitEnquiry = async (formData) => {
    const latestNotice = latestTurn?.components?.find((c) => c.type === 'EnquiryNotice' && (c.public_reference || c.reference));
    const res = await api('/enquiries/contact', {
      method: 'POST',
      body: JSON.stringify({
        enquiry_id: activeQuote?.enquiry || latestNotice?.reference || latestNotice?.public_reference || null,
        quote_id: activeQuote?.id || null,
        trip_id: sessionStorage.getItem('mira-workspace-trip') || null,
        name: formData.name,
        email: formData.email,
        phone: formData.phone || '',
        tour_id: activeTour?.id || null,
        tour_title: activeTour?.title || '',
        date: formData.date || travellerConfig.date || '',
        adults: Number(travellerConfig.adults || 2),
        child_ages: travellerConfig.childAges || [],
        notes: formData.notes || '',
      }),
    });
    return res.reference || res.id;
  };

  const suggestions = [
    { label: 'Find a day tour', icon: Clock },
    { label: 'Find a day trip', icon: Compass },
    { label: 'Explore multi-day trips', icon: Calendar },
    { label: 'Plan a family holiday', icon: Users },
    { label: 'Create a custom trip', icon: Sparkles },
  ];

  const latestTurn = items[items.length - 1]?.turn;

  return (
    <div data-a2ui-version="1" className="h-[calc(100vh-64px)] flex flex-col lg:flex-row">
      {/* Mobile Tab Switcher */}
      <div className="lg:hidden flex border-b border-border bg-white px-4 py-2 gap-2">
        <button
          type="button"
          onClick={() => setMobileTab('chat')}
          className={`flex-1 py-1.5 text-xs font-semibold rounded-pill cursor-pointer transition-colors ${
            mobileTab === 'chat' ? 'bg-brand-orange text-white' : 'bg-gray-100 text-text-muted'
          }`}
        >
          Conversation
        </button>
        <button
          type="button"
          onClick={() => { setMobileTab('workspace'); setWorkspaceUpdated(false); }}
          className={`flex-1 py-1.5 text-xs font-semibold rounded-pill cursor-pointer transition-colors flex items-center justify-center gap-1.5 ${
            mobileTab === 'workspace' ? 'bg-brand-orange text-white' : 'bg-gray-100 text-text-muted'
          }`}
        >
          <span>Workspace {workspacePanel !== 'welcome' && `(${workspacePanel})`}</span>
          {workspaceUpdated && mobileTab !== 'workspace' && (
            <span className="w-2 h-2 rounded-full bg-brand-orange animate-pulse" aria-label="Workspace updated" />
          )}
        </button>
      </div>

      {/* Left Panel - Conversation */}
      <div className={`${mobileTab === 'chat' ? 'flex' : 'hidden'} lg:flex w-full lg:w-[40%] border-r border-border flex-col bg-white`}>
        <div className="p-4 border-b border-border flex items-center gap-3">
          <div className="w-9 h-9 rounded-full bg-brand-teal/10 flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-brand-teal" />
          </div>
          <div>
            <h2 className="font-semibold text-sm">Mira</h2>
            <p className="text-xs text-text-muted">AI Travel Companion</p>
          </div>
          <div className="ml-auto flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full bg-brand-leaf animate-pulse" />
            <span className="text-xs text-text-muted">Online</span>
            {items.length > 0 && <Button variant="ghost" size="sm" onClick={newTrip} disabled={!ready || isTyping}>New Trip</Button>}
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto custom-scroll p-4 space-y-4">
          <div className="flex gap-3 fade-in">
            <div className="w-7 h-7 rounded-full bg-brand-teal/10 flex items-center justify-center flex-shrink-0">
              <Sparkles className="w-3.5 h-3.5 text-brand-teal" />
            </div>
            <div className="max-w-[80%] bg-gray-50 rounded-card rounded-tl-none p-3">
              <p className="text-sm leading-relaxed">Hello, I'm Mira. What kind of Sri Lankan adventure are you planning?</p>
            </div>
          </div>

          {items.map((item, idx) => (
            <React.Fragment key={idx}>
              {/* User Prompt */}
              <div className="flex gap-3 justify-end fade-in">
                <div className="max-w-[80%] bg-brand-orange/10 rounded-card rounded-tr-none p-3">
                  <p className="text-sm leading-relaxed">{formatUserMessage(item, tours)}</p>
                </div>
                <div className="w-7 h-7 rounded-full bg-gray-200 flex items-center justify-center flex-shrink-0">
                  <Users className="w-3.5 h-3.5 text-gray-500" />
                </div>
              </div>

              {/* Assistant Turn */}
              <div className="flex gap-3 fade-in">
                <div className="w-7 h-7 rounded-full bg-brand-teal/10 flex items-center justify-center flex-shrink-0">
                  <Sparkles className="w-3.5 h-3.5 text-brand-teal" />
                </div>
                <div className="max-w-[80%] bg-gray-50 rounded-card rounded-tl-none p-3 space-y-2">
                  <p className="text-sm leading-relaxed">{item.turn.text}</p>
                  {/* Inline UI Components */}
                  {(() => {
                    const comps = item.turn.components || [];
                    const quoteComp = comps.find((c) => c.type === 'PriceBreakdown' && c.quote);
                    const hasQuote = Boolean(quoteComp);
                    const allowed = [
                      'TourCard', 'TravellerPicker', 'PriceBreakdown', 'EnquiryNotice',
                      'ItineraryDay', 'PolicySnippet', 'DestinationHighlight', 'DestinationCard',
                      'StayCard', 'ActivityCard', 'ComparisonPanel', 'ConfirmationPanel',
                      'SourceReference', 'JourneyPlan', 'BookingForm',
                      'CancellationPreview', 'CancellationStatus',
                    ];
                    return comps
                      .filter((c) => allowed.includes(c.type))
                      .filter((c) => !hasQuote || !['TourCard', 'ItineraryDay', 'SourceReference', 'BookingForm'].includes(c.type))
                      .map((c, cIdx) => (
                        <div key={`${c.type}-${cIdx}`} className="pt-2 border-t border-border/50">
                          <UIComponentRenderer 
                            component={c} 
                            enquiryReference={quoteComp?.quote?.enquiry_reference}
                            navigate={navigate} 
                            tours={tours} 
                            setActiveTour={handleSelectTour}
                            onSend={send}
                            setWorkspacePanel={(panel) => {
                              setWorkspacePanel(panel);
                              setMobileTab('workspace');
                              setWorkspaceUpdated(false);
                            }} 
                          />
                        </div>
                      ));
                  })()}
                </div>
              </div>
            </React.Fragment>
          ))}

          {isTyping && (
            <div className="flex gap-3 fade-in">
              <div className="w-7 h-7 rounded-full bg-brand-teal/10 flex items-center justify-center flex-shrink-0">
                <Sparkles className="w-3.5 h-3.5 text-brand-teal" />
              </div>
              <div className="bg-gray-50 rounded-card rounded-tl-none p-3">
                <div className="flex gap-1.5">
                  <div className="w-2 h-2 rounded-full bg-text-muted typing-dot" />
                  <div className="w-2 h-2 rounded-full bg-text-muted typing-dot" />
                  <div className="w-2 h-2 rounded-full bg-text-muted typing-dot" />
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Suggestions */}
        {items.length === 0 && (
          <div className="px-4 pb-2">
            <div className="grid grid-cols-2 gap-2">
              {suggestions.map(s => {
                const Icon = s.icon;
                return (
                  <button 
                    key={s.label}
                    disabled={!ready || isTyping}
                    onClick={() => handleSend(s.label)}
                    className="flex items-center gap-2 p-3 border border-border rounded-card text-sm text-left hover:border-brand-orange transition-colors cursor-pointer disabled:opacity-50"
                  >
                    <Icon className="w-4 h-4 text-brand-teal" />
                    <span>{s.label}</span>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Error / Recovery Alert */}
        {error && (
          <div className="px-4 py-2 bg-red-50 border-t border-red-200 text-red-700 text-xs flex items-center justify-between" role="alert">
            <span>{error}</span>
            <Button variant="ghost" size="sm" onClick={retry} className="text-red-700 underline font-semibold p-0">
              Retry
            </Button>
          </div>
        )}

        {/* Privacy Consent Checkbox */}
        <div className="px-4 py-2 border-t border-border flex items-center gap-2">
          <input
            id="remember-journey-checkbox"
            type="checkbox"
            checked={remember}
            disabled={!ready || privacyBusy || isTyping}
            onChange={(e) => consent(e.target.checked)}
            className="cursor-pointer"
          />
          <label htmlFor="remember-journey-checkbox" className="text-xs text-text-muted select-none cursor-pointer">
            Remember this journey on this device for 30 days
          </label>
        </div>

        {/* Input */}
        <div className="p-4 border-t border-border">
          <div className="flex gap-2">
            <input 
              type="text"
              aria-label="Message Mira"
              maxLength={1200}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleSend(); }}
              placeholder="Tell Mira what you're looking for..."
              disabled={!ready || isTyping}
              className="flex-1 px-4 py-3 border border-border rounded-input text-sm focus:outline-none focus:border-brand-orange disabled:bg-gray-50"
            />
            <Button 
              variant="primary" 
              onClick={() => handleSend()} 
              aria-label="Send message"
              disabled={!ready || isTyping || !input.trim()}
            >
              <Send className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Right Panel - Workspace */}
      <div 
        className={`${mobileTab === 'workspace' ? 'flex' : 'hidden'} lg:flex w-full lg:w-[60%] flex-col bg-gray-50/50`}
      >
        <div className="p-6 border-b border-border bg-white flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-sm">Travel Workspace</h3>
            <p className="text-xs text-text-muted">Interactive components update as you chat with Mira</p>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto custom-scroll p-6">
          {workspacePanel === 'welcome' && <WelcomePanel navigate={navigate} />}
          {workspacePanel === 'suggestions' && <SuggestionsPanel handleSelect={(t) => handleSend(t)} tours={tours} />}
          {workspacePanel === 'tour-detail' && activeTour && (
            <TourDetailPanel 
              tour={activeTour} 
              navigate={navigate} 
              onGetQuote={(t) => { handleSelectTour(t); setWorkspacePanel('traveller-picker'); }}
              onExploreItinerary={(t) => { handleSelectTour(t); setWorkspacePanel('traveller-picker'); }}
            />
          )}
          {workspacePanel === 'traveller-picker' && (
            <TravellerPickerPanel 
              config={travellerConfig} 
              setConfig={next => { editedSinceSend.current = true; setTravellerConfig(next); }} 
              onCheckRates={handleCheckRates}
              tour={activeTour}
              isQuoting={isTyping}
            />
          )}
          {workspacePanel === 'quote' && activeQuote && (
            <PriceBreakdownPanel 
              tour={activeTour} 
              quote={activeQuote} 
              config={travellerConfig}
              onRecalculate={() => setWorkspacePanel('traveller-picker')}
              onSendEnquiry={() => setWorkspacePanel('booking-form')} 
              onMockBooking={handleMockBooking}
              mockBookingStatus={mockBookingStatus}
              confirmedBookingRef={confirmedBookingRef}
              navigate={navigate}
            />
          )}
          {workspacePanel === 'booking-form' && (
            <BookingFormPanel 
              tour={activeTour} 
              quote={activeQuote} 
              navigate={navigate} 
              onSubmitEnquiry={handleSubmitEnquiry}
            />
          )}
          {workspacePanel === 'itinerary' && itineraryCards.length > 0 && (
            <div className="space-y-4 fade-in">
              <div className="flex items-center justify-between">
                <h4 className="font-bold text-md">{activeTour?.title || 'Itinerary Highlights'}</h4>
                {activeTour && (
                  <Button variant="primary" size="sm" onClick={() => setWorkspacePanel('traveller-picker')}>
                    Check rates
                  </Button>
                )}
              </div>
              {itineraryCards.map((day, dIdx) => (
                <Card key={dIdx} className="p-5 space-y-2" data-component-type="ItineraryDay">
                  <div className="flex items-center justify-between gap-2">
                    <h5 className="font-semibold text-sm text-brand-black">{day.heading}</h5>
                    <span className="text-[11px] font-medium px-2 py-0.5 rounded-pill bg-brand-teal/10 text-brand-teal">
                      Published Guide
                    </span>
                  </div>
                  <div className="text-xs text-text-muted leading-relaxed">
                    <MarkdownContent content={day.text} />
                  </div>
                </Card>
              ))}
            </div>
          )}
          {workspacePanel === 'custom-enquiry' && <CustomEnquiryPanel navigate={navigate} />}
          {workspacePanel === 'journey-plan' && journeyPlan && <JourneyPlanPanel key={latestTurn.trace} plan={journeyPlan}
            map={latestTurn.components.find(c => c.type === 'InteractiveMap')} />}
        </div>
      </div>
    </div>
  );
}

// ============ WORKSPACE PANELS ============
function WelcomePanel({ navigate }) {
  return (
    <div className="text-center py-12 fade-in">
      <div className="w-16 h-16 rounded-full bg-brand-teal/10 flex items-center justify-center mx-auto mb-6">
        <Sparkles className="w-8 h-8 text-brand-teal" />
      </div>
      <h3 className="text-lg font-bold mb-2">Your Travel Workspace</h3>
      <p className="text-sm text-text-muted mb-8 max-w-sm mx-auto">
        As you chat with Mira, relevant tour cards, pricing and booking components will appear here.
      </p>
      <div className="grid grid-cols-2 gap-3 max-w-sm mx-auto">
        {[
          { icon: MapPin, label: 'Destinations', path: '/destinations' },
          { icon: Compass, label: 'All Tours', path: '/tours' },
          { icon: BookOpen, label: 'Policies', path: '/policies' },
          { icon: Info, label: 'About Us', path: '/about' },
        ].map(item => {
          const Icon = item.icon;
          return (
            <button key={item.label} onClick={() => navigate(item.path)} className="flex flex-col items-center gap-2 p-4 border border-border rounded-card hover:border-brand-orange transition-colors cursor-pointer">
              <Icon className="w-5 h-5 text-brand-teal" />
              <span className="text-xs font-medium">{item.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

function SuggestionsPanel({ handleSelect, tours }) {
  const items = [
    { title: 'Sigiriya and Minneriya Day Tour from Kandy', desc: 'Day tour from Kandy', id: 'T01' },
    { title: 'Cultural Triangle Sri Lanka Package', desc: '7-day round trip', id: 'T09' },
    { title: 'Highlights of Sri Lanka', desc: '8-day comprehensive journey', id: 'T05' },
    { title: 'Galle Coastal Experience', desc: '4-day beach and fort', id: 'T08' },
  ];
  return (
    <div className="space-y-3 fade-in">
      <h4 className="font-semibold text-sm mb-4">Recommended tours</h4>
      {items.map(item => {
        const tour = tours.find(t => t.id === item.id) || tours[0];
        return (
          <Card key={item.id} className="p-4 cursor-pointer" onClick={() => handleSelect(`Tell me about ${item.title}`)}>
            <div className="flex items-center gap-3">
              <div className={`w-12 h-12 rounded-lg ${tour.imgClass || 'tour-img-1'} flex-shrink-0`} />
              <div>
                <h5 className="font-semibold text-sm">{item.title}</h5>
                <p className="text-xs text-text-muted">{item.desc}</p>
              </div>
            </div>
          </Card>
        );
      })}
    </div>
  );
}

function TourDetailPanel({ tour, navigate, onGetQuote, onExploreItinerary }) {
  return (
    <div className="fade-in space-y-6" data-tour-id={tour.id}>
      <Card className="overflow-hidden">
        <div className={`${tour.imgClass || 'tour-img-1'} h-40 relative`}>
          <div className="absolute inset-0 bg-gradient-to-t from-black/40 to-transparent" />
          <div className="absolute bottom-4 left-4">
            <span className="bg-white/90 text-xs font-semibold px-2 py-1 rounded-pill">{tour.category}</span>
          </div>
        </div>
        <div className="p-5">
          <h3 className="font-bold text-md mb-2">{tour.title}</h3>
          <div className="flex flex-wrap gap-3 text-xs text-text-muted mb-3">
            <span className="flex items-center gap-1"><Clock className="w-3.5 h-3.5" />{tour.duration}</span>
            <span className="flex items-center gap-1"><MapPin className="w-3.5 h-3.5" />{tour.start}</span>
          </div>
          <p className="text-sm text-text-muted mb-4">{tour.description}</p>
          <div className="flex flex-wrap gap-2">
            <Button variant="primary" size="sm" onClick={() => navigate(`/tours/${tour.slug}`)}>View full details</Button>
            <Button variant="secondary" size="sm" onClick={() => onGetQuote(tour)}>Get a quote</Button>
            <Button variant="ghost" size="sm" onClick={() => onExploreItinerary(tour)}>Explore itinerary</Button>
          </div>
        </div>
      </Card>

      {tour.itinerary?.length > 0 && (
        <div>
          <h4 className="font-semibold text-sm mb-3">Itinerary preview</h4>
          <div className="space-y-2">
            {tour.itinerary.slice(0, 3).map(day => (
              <div key={day.day} className="flex gap-3 p-3 bg-white border border-border rounded-card">
                <div className="w-7 h-7 rounded-full bg-brand-orange/10 flex items-center justify-center flex-shrink-0">
                  <span className="text-brand-orange text-xs font-bold">{day.day}</span>
                </div>
                <div>
                  <p className="text-sm font-medium">{day.title}</p>
                  <p className="text-xs text-text-muted line-clamp-1">{day.description}</p>
                </div>
              </div>
            ))}
            {tour.itinerary.length > 3 && (
              <p className="text-xs text-text-muted text-center">+{tour.itinerary.length - 3} more days</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function TravellerPickerPanel({ config, setConfig, onCheckRates, tour, isQuoting }) {
  return (
    <div className="fade-in">
      <Card className="p-6">
        <h4 className="font-semibold text-md mb-1">Traveller details</h4>
        <p className="text-xs text-text-muted mb-6">Select your group composition and travel date for accurate pricing.</p>
        
        <form onSubmit={(e) => { e.preventDefault(); onCheckRates(); }} className="space-y-5">
          <div>
            <label htmlFor="tp-travel-date" className="text-sm font-medium block mb-2">Travel date</label>
            <input 
              id="tp-travel-date"
              type="date"
              value={config.date || ''}
              onChange={(e) => setConfig({ ...config, date: e.target.value })}
              className="w-full px-3 py-2.5 border border-border rounded-input text-sm focus:outline-none focus:border-brand-orange"
            />
          </div>

          <div>
            <label htmlFor="tp-adults" className="text-sm font-medium block mb-2">Adults</label>
            <div className="flex items-center border border-border rounded-input">
              <button type="button" onClick={() => setConfig({...config, adults: Math.max(1, config.adults - 1)})} className="px-4 py-3 cursor-pointer"><Minus className="w-4 h-4" /></button>
              <input 
                id="tp-adults"
                aria-label="Adults"
                type="number"
                min="1"
                max="30"
                value={config.adults}
                onChange={(e) => setConfig({...config, adults: Math.max(1, parseInt(e.target.value) || 1)})}
                className="flex-1 text-center font-semibold bg-transparent border-none focus:outline-none"
              />
              <button type="button" onClick={() => setConfig({...config, adults: config.adults + 1})} className="px-4 py-3 cursor-pointer"><Plus className="w-4 h-4" /></button>
            </div>
          </div>

          <div>
            <label className="text-sm font-medium block mb-2">Children (ages 2–11)</label>
            <div className="flex items-center border border-border rounded-input">
              <button type="button" onClick={() => {
                const count = Math.max(0, config.children - 1);
                setConfig({...config, children: count, childAges: config.childAges.slice(0, count)});
              }} className="px-4 py-3 cursor-pointer"><Minus className="w-4 h-4" /></button>
              <span className="flex-1 text-center font-semibold">{config.children}</span>
              <button type="button" onClick={() => {
                const count = config.children + 1;
                setConfig({...config, children: count, childAges: [...config.childAges, 7]});
              }} className="px-4 py-3 cursor-pointer"><Plus className="w-4 h-4" /></button>
            </div>
          </div>

          <div>
            <label htmlFor="tp-child-ages" className="text-sm font-medium block mb-1">Child ages, separated by commas</label>
            <input
              id="tp-child-ages"
              type="text"
              placeholder="e.g. 5, 8"
              value={config.childAges?.join(", ") || ""}
              onChange={(e) => {
                const parts = e.target.value.split(",").map(s => parseInt(s.trim())).filter(n => !isNaN(n));
                setConfig({ ...config, childAges: parts, children: parts.length });
              }}
              className="w-full px-3 py-2 border border-border rounded-input text-sm"
            />
          </div>

          <div>
            <label className="text-sm font-medium block mb-2">Infants (under 2)</label>
            <div className="flex items-center border border-border rounded-input">
              <button type="button" onClick={() => setConfig({...config, infants: Math.max(0, (config.infants || 0) - 1)})} className="px-4 py-3 cursor-pointer"><Minus className="w-4 h-4" /></button>
              <span className="flex-1 text-center font-semibold">{config.infants || 0}</span>
              <button type="button" onClick={() => setConfig({...config, infants: (config.infants || 0) + 1})} className="px-4 py-3 cursor-pointer"><Plus className="w-4 h-4" /></button>
            </div>
          </div>

          <div className="mt-6 p-3 bg-brand-teal/5 rounded-card">
            <p className="text-xs text-brand-teal">
              <Info className="w-3.5 h-3.5 inline mr-1" />
              Children aged 2–11 receive child pricing. Infants under 2 travel free under stated conditions.
            </p>
          </div>

          <Button type="submit" variant="primary" className="w-full" disabled={isQuoting || !config.date}>
            {isQuoting ? "Checking rates..." : "Check rates"}
          </Button>
        </form>
      </Card>
    </div>
  );
}

function PriceBreakdownPanel({ tour, quote, config, onRecalculate, onSendEnquiry, onMockBooking, mockBookingStatus, confirmedBookingRef, navigate }) {
  if (!quote) return null;
  const combinedConfigAges = config ? partyAges(config) : [];
  const isCompatible = config ? isQuoteCompatible(quote, tour?.id, config.date, config.adults, combinedConfigAges.length, combinedConfigAges) : true;
  return (
    <div className="fade-in" role="region" aria-label={isCompatible ? "Verified quote" : "Outdated quote"}>
      <Card className={`p-6 ${isCompatible ? 'border-brand-leaf/40' : 'border-amber-300 bg-amber-50/20'}`}>
        <div className="flex items-center justify-between mb-4">
          {isCompatible ? (
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-brand-leaf animate-pulse" />
              <span className="text-xs font-semibold text-brand-leaf uppercase tracking-wider">Verified Quote</span>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-amber-500" />
              <span className="text-xs font-semibold text-amber-700 uppercase tracking-wider">Quote Outdated</span>
            </div>
          )}
          {quote.enquiry && (
            <button onClick={() => navigate('/enquiry/' + quote.enquiry)} className="text-xs text-brand-teal hover:underline font-medium">
              View enquiry status
            </button>
          )}
        </div>

        {!isCompatible && config && (
          <div className="mb-4 p-3 bg-amber-100/80 border border-amber-200 rounded-input text-xs text-amber-900 leading-relaxed">
            <strong>Trip Details Changed:</strong> Active configuration is <strong>{config.adults} adult{config.adults > 1 ? 's' : ''}{config.children > 0 ? `, ${config.children} child(ren)` : ''}{config.infants > 0 ? `, ${config.infants} infant(s)` : ''}</strong> on <strong>{config.date}</strong>. This rate was calculated for {quote.adults} adult{quote.adults > 1 ? 's' : ''} on {quote.date}.
            {onRecalculate && (
              <button onClick={onRecalculate} className="block mt-2 font-bold underline text-amber-900 cursor-pointer">
                Recalculate quote for current group →
              </button>
            )}
          </div>
        )}
        
        <h4 className="font-bold text-md mb-1">{quote.title || tour?.title}</h4>
        <p className="text-xs text-text-muted mb-6 font-mono">Quote #{quote.id?.slice(0, 8).toUpperCase()}</p>

        <div className="space-y-3 mb-6">
          <div className="flex justify-between text-sm">
            <span className="text-text-muted">Travellers</span>
            <span className="font-medium">
              {quote.adults} adult{quote.adults > 1 ? 's' : ''}
              {quote.ages?.length ? ` (ages ${quote.ages.join(', ')})` : ''}
            </span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-text-muted">Duration</span>
            <span className="font-medium">{tour?.duration || 'Tour itinerary'}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-text-muted">Travel date</span>
            <span className="font-medium">{quote.date}</span>
          </div>
        </div>

        <div className="border-t border-border pt-4 space-y-3">
          <div className="flex justify-between items-center">
            <span className="font-semibold">Verified tour price</span>
            <span className={`text-xl font-bold ${isCompatible ? 'text-brand-black' : 'text-text-muted line-through'}`}>
              {quote.currency || 'USD'} {quote.total?.toLocaleString()}
            </span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-text-muted">Deposit required</span>
            <span className="font-medium">{quote.currency || 'USD'} {quote.deposit?.toLocaleString()}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-text-muted">Balance</span>
            <span className="font-medium">{quote.currency || 'USD'} {quote.balance?.toLocaleString()}</span>
          </div>
        </div>

        {quote.enquiry && (
          <div className="mt-4 p-3 rounded-card bg-brand-leaf/10 border border-brand-leaf/25 text-xs space-y-1">
            <p className="font-semibold text-brand-leaf">Quote &amp; private enquiry saved</p>
            {quote.enquiry_reference && (
              <p className="font-mono text-brand-black">Enquiry ref: {quote.enquiry_reference}</p>
            )}
          </div>
        )}

        <div className="mt-4 p-3 bg-brand-sun/10 rounded-card">
          <p className="text-xs text-brand-black">
            <AlertCircle className="w-3.5 h-3.5 inline mr-1" />
            {quote.validity === 'recheck_before_booking' ? 'Rate re-check recommended before final booking.' : 'This quote is valid for 48 hours.'} Deposit is payable on confirmation.
          </p>
        </div>

        <div className="mt-5 p-3.5 rounded-card border border-dashed border-border bg-gray-50/70">
          <label htmlFor="mock-booking-outcome" className="text-[11px] font-semibold uppercase tracking-wide block mb-2 text-text-muted">
            Simulated checkout (demo only — no real payment)
          </label>
          <div className="flex gap-2">
            <select id="mock-booking-outcome" aria-label="Mock booking outcome" className="px-3 py-2 border border-border rounded-input text-xs flex-1">
              <option value="success">success</option>
              <option value="declined">declined</option>
              <option value="unavailable">unavailable</option>
              <option value="network">network error</option>
              <option value="expired">expired</option>
            </select>
            <Button 
              variant="secondary" 
              size="sm" 
              disabled={!isCompatible}
              title={!isCompatible ? "Recalculate quote to book with updated details" : "Try mock booking"}
              onClick={() => {
                const val = document.getElementById('mock-booking-outcome')?.value || 'success';
                onMockBooking(quote.id, val);
              }}
            >
              Try mock booking
            </Button>
          </div>
          {!isCompatible && (
            <p className="mt-1.5 text-[11px] text-amber-700">
              Cannot book an outdated quote. Update group configuration and recalculate.
            </p>
          )}
          {confirmedBookingRef && (
            <div className="mt-2 p-2.5 rounded-input bg-emerald-50 border border-emerald-200 text-xs text-emerald-900">
              <strong>Demo booking: Confirmed</strong> (Simulation ref #{confirmedBookingRef.slice(0, 8).toUpperCase()})
            </div>
          )}
          {mockBookingStatus && (
            <div className="mt-2 text-xs font-semibold" role="status">
              {mockBookingStatus === 'confirmed' ? (
                <span className="text-brand-teal">Demo booking: Confirmed (simulated — no real payment)</span>
              ) : (
                <span className="text-amber-800">
                  Latest simulated payment attempt <span className="uppercase">{mockBookingStatus}</span>. Your quote and enquiry remain saved — you can retry checkout or send an enquiry.
                </span>
              )}
            </div>
          )}
        </div>

        <div className="mt-4 flex gap-2">
          {quote.enquiry ? (
            <>
              <Button variant="primary" className="flex-1" onClick={onSendEnquiry}>Add contact details</Button>
              <Button variant="secondary" className="flex-1" onClick={() => navigate('/enquiry/' + (quote.enquiry_reference || quote.enquiry))}>
                View enquiry
              </Button>
            </>
          ) : (
            <Button variant="primary" className="flex-1" onClick={onSendEnquiry}>Send enquiry</Button>
          )}
        </div>
      </Card>
    </div>
  );
}

function BookingFormPanel({ tour, quote, navigate, onSubmitEnquiry }) {
  const { user } = useAuth();
  const [submitted, setSubmitted] = useState(false);
  const [ref, setRef] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [formData, setFormData] = useState({
    name: user?.full_name || '',
    email: user?.email || '',
    phone: user?.phone || '',
    date: quote?.date || '',
    notes: '',
  });

  useEffect(() => {
    if (user) {
      setFormData((prev) => ({
        ...prev,
        name: prev.name || user.full_name || '',
        email: prev.email || user.email || '',
        phone: prev.phone || user.phone || '',
      }));
    }
  }, [user]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setErrorMsg('');
    try {
      const reference = await onSubmitEnquiry(formData);
      setRef(reference);
      setSubmitted(true);
    } catch (err) {
      setErrorMsg(err.message || "Failed to submit enquiry.");
    } finally {
      setSubmitting(false);
    }
  };

  if (submitted) {
    return (
      <div className="fade-in text-center py-12">
        <div className="w-16 h-16 rounded-full bg-brand-leaf/10 flex items-center justify-center mx-auto mb-4">
          <Check className="w-8 h-8 text-brand-leaf" />
        </div>
        <h3 className="font-bold text-md mb-2">Enquiry submitted</h3>
        <p className="text-sm text-text-muted mb-4">Your enquiry has been saved. Our team will review the details and follow up.</p>
        <p className="text-xs font-mono bg-gray-50 px-3 py-2 rounded-input inline-block mb-6">Reference: {ref}</p>
        <div className="space-y-2">
          <Button variant="primary" onClick={() => navigate(`/enquiry/${ref}`)}>View enquiry</Button>
          <br />
          <Button variant="ghost" onClick={() => navigate('/')}>Back to home</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="fade-in">
      <Card className="p-6">
        <h4 className="font-semibold text-md mb-1">Send an enquiry</h4>
        <p className="text-xs text-text-muted mb-6">Our team will confirm availability and pricing for {tour?.title || 'your trip'}.</p>
        {errorMsg && (
          <div className="mb-4 p-3 rounded-input text-xs bg-red-50 text-red-800 border border-red-200 flex items-start gap-2" role="alert">
            <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
            <span>{errorMsg}</span>
          </div>
        )}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="booking-name" className="text-xs font-medium block mb-1">Full name *</label>
            <input 
              id="booking-name"
              type="text" 
              required 
              value={formData.name}
              onChange={(e) => setFormData({...formData, name: e.target.value})}
              className="w-full px-3 py-2.5 border border-border rounded-input text-sm focus:outline-none focus:border-brand-orange" 
            />
          </div>
          <div>
            <label htmlFor="booking-email" className="text-xs font-medium block mb-1">Email *</label>
            <input 
              id="booking-email"
              type="email" 
              required 
              value={formData.email}
              onChange={(e) => setFormData({...formData, email: e.target.value})}
              className="w-full px-3 py-2.5 border border-border rounded-input text-sm focus:outline-none focus:border-brand-orange" 
            />
          </div>
          <div>
            <label htmlFor="booking-phone" className="text-xs font-medium block mb-1">Phone number (optional)</label>
            <input 
              id="booking-phone"
              type="tel" 
              value={formData.phone}
              onChange={(e) => setFormData({...formData, phone: e.target.value})}
              placeholder="+94 77 123 4567"
              className="w-full px-3 py-2.5 border border-border rounded-input text-sm focus:outline-none focus:border-brand-orange" 
            />
          </div>
          <div>
            <label htmlFor="booking-date" className="text-xs font-medium block mb-1">Preferred travel date</label>
            <input 
              id="booking-date"
              type="date" 
              value={formData.date}
              onChange={(e) => setFormData({...formData, date: e.target.value})}
              className="w-full px-3 py-2.5 border border-border rounded-input text-sm focus:outline-none focus:border-brand-orange" 
            />
          </div>
          <div>
            <label htmlFor="booking-notes" className="text-xs font-medium block mb-1">Notes</label>
            <textarea 
              id="booking-notes"
              rows={3} 
              value={formData.notes}
              onChange={(e) => setFormData({...formData, notes: e.target.value})}
              className="w-full px-3 py-2.5 border border-border rounded-input text-sm focus:outline-none focus:border-brand-orange resize-none" 
              placeholder="Any special requirements..." 
            />
          </div>
          <Button type="submit" variant="primary" className="w-full" disabled={submitting}>
            {submitting ? "Submitting..." : "Submit enquiry"}
          </Button>
        </form>
      </Card>
    </div>
  );
}

function CustomEnquiryPanel({ navigate }) {
  const { user } = useAuth();
  const [name, setName] = useState(user?.full_name || '');
  const [email, setEmail] = useState(user?.email || '');
  const [phone, setPhone] = useState(user?.phone || '');
  const [destinations, setDestinations] = useState('');
  const [duration, setDuration] = useState('7–10 days');
  const [groupSize, setGroupSize] = useState('3–4 people');
  const [selectedInterests, setSelectedInterests] = useState([]);
  const [submittedRef, setSubmittedRef] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    if (user) {
      setName((p) => p || user.full_name || '');
      setEmail((p) => p || user.email || '');
      setPhone((p) => p || user.phone || '');
    }
  }, [user]);

  const toggleInterest = (interest) => {
    setSelectedInterests(prev => 
      prev.includes(interest) ? prev.filter(i => i !== interest) : [...prev, interest]
    );
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setErrorMsg('');
    try {
      const notes = `Custom trip request (${duration}, ${groupSize}): ${destinations || 'Flexible destinations'}${selectedInterests.length ? '. Interests: ' + selectedInterests.join(', ') : ''}`;
      const res = await api('/enquiries/contact', {
        method: 'POST',
        body: JSON.stringify({
          trip_id: sessionStorage.getItem('mira-workspace-trip') || null,
          name,
          email,
          phone,
          tour_title: destinations ? `Custom Trip: ${destinations}` : 'Custom Sri Lanka Journey',
          adults: groupSize.startsWith('1') ? 2 : groupSize.startsWith('3') ? 4 : 6,
          notes,
        }),
      });
      setSubmittedRef(res.reference || res.id);
    } catch (err) {
      setErrorMsg(err.message || 'Failed to submit custom request.');
    } finally {
      setSubmitting(false);
    }
  };

  if (submittedRef) {
    return (
      <div className="fade-in text-center py-12">
        <div className="w-16 h-16 rounded-full bg-brand-leaf/10 flex items-center justify-center mx-auto mb-4">
          <Check className="w-8 h-8 text-brand-leaf" />
        </div>
        <h3 className="font-bold text-md mb-2">Custom Request Received</h3>
        <p className="text-sm text-text-muted mb-4">Our specialist team is preparing your custom itinerary.</p>
        <p className="text-xs font-mono bg-gray-50 px-3 py-2 rounded-input inline-block mb-6">Reference: {submittedRef}</p>
        <div className="space-y-2">
          <Button variant="primary" onClick={() => navigate(`/enquiry/${submittedRef}`)}>View enquiry status</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="fade-in">
      <Card className="p-6">
        <div className="text-center mb-6">
          <div className="w-12 h-12 rounded-full bg-brand-orange/10 flex items-center justify-center mx-auto mb-3">
            <Sparkles className="w-6 h-6 text-brand-orange" />
          </div>
          <h4 className="font-semibold text-md">Custom Trip Request</h4>
          <p className="text-xs text-text-muted mt-1">Our team will create a personalised itinerary for you.</p>
        </div>
        {errorMsg && (
          <div className="mb-4 p-3 rounded-input text-xs bg-red-50 text-red-800 border border-red-200 flex items-start gap-2" role="alert">
            <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
            <span>{errorMsg}</span>
          </div>
        )}
        <form className="space-y-4" onSubmit={handleSubmit}>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label htmlFor="custom-name" className="text-xs font-medium block mb-1">Full name *</label>
              <input
                id="custom-name"
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Your name"
                className="w-full px-3 py-2.5 border border-border rounded-input text-sm focus:outline-none focus:border-brand-orange"
              />
            </div>
            <div>
              <label htmlFor="custom-email" className="text-xs font-medium block mb-1">Email *</label>
              <input
                id="custom-email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                className="w-full px-3 py-2.5 border border-border rounded-input text-sm focus:outline-none focus:border-brand-orange"
              />
            </div>
          </div>
          <div>
            <label htmlFor="custom-phone" className="text-xs font-medium block mb-1">Phone number (optional)</label>
            <input
              id="custom-phone"
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+94 77 123 4567"
              className="w-full px-3 py-2.5 border border-border rounded-input text-sm focus:outline-none focus:border-brand-orange"
            />
          </div>
          <div>
            <label htmlFor="custom-destinations" className="text-xs font-medium block mb-1">Destinations of interest</label>
            <input 
              id="custom-destinations"
              type="text" 
              value={destinations}
              onChange={(e) => setDestinations(e.target.value)}
              className="w-full px-3 py-2.5 border border-border rounded-input text-sm focus:outline-none focus:border-brand-orange" 
              placeholder="e.g. Kandy, Ella, Mirissa" 
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="custom-duration" className="text-xs font-medium block mb-1">Duration</label>
              <select 
                id="custom-duration"
                value={duration} 
                onChange={(e) => setDuration(e.target.value)}
                className="w-full px-3 py-2.5 border border-border rounded-input text-sm"
              >
                <option>5–7 days</option>
                <option>7–10 days</option>
                <option>10–14 days</option>
                <option>14+ days</option>
              </select>
            </div>
            <div>
              <label htmlFor="custom-group-size" className="text-xs font-medium block mb-1">Group size</label>
              <select 
                id="custom-group-size"
                value={groupSize}
                onChange={(e) => setGroupSize(e.target.value)}
                className="w-full px-3 py-2.5 border border-border rounded-input text-sm"
              >
                <option>1–2 people</option>
                <option>3–4 people</option>
                <option>5–8 people</option>
                <option>8+ people</option>
              </select>
            </div>
          </div>
          <div>
            <label className="text-xs font-medium block mb-1">Interests</label>
            <div className="flex flex-wrap gap-2">
              {['Culture', 'Wildlife', 'Beaches', 'Hiking', 'Food', 'Relaxation'].map(i => (
                <Chip key={i} active={selectedInterests.includes(i)} onClick={() => toggleInterest(i)}>{i}</Chip>
              ))}
            </div>
          </div>
          <Button type="submit" variant="primary" className="w-full" disabled={submitting}>
            {submitting ? 'Submitting...' : 'Submit request'}
          </Button>
        </form>
      </Card>
    </div>
  );
}

function JourneyPlanPanel({ plan, map }) {
  const [selectedDay, setSelectedDay] = useState(plan.selected || 0);
  const photo = photos[destinationPhotos[plan.days[selectedDay]?.source]];
  return (
    <div className="fade-in space-y-4" data-component-type="JourneyPlan" aria-label="Journey workspace">
      <div className="flex items-center justify-between">
        <h4 className="font-semibold text-md">Custom Journey Itinerary</h4>
        <span className="text-xs text-brand-orange font-medium">{plan.days.length} Days</span>
      </div>
      <div className="flex gap-2 overflow-x-auto pb-2 day-tabs">
        {plan.days.map((day, idx) => (
          <button
            key={idx}
            onClick={() => setSelectedDay(idx)}
            className={`px-3 py-1.5 rounded-pill text-xs font-medium cursor-pointer transition-colors ${
              selectedDay === idx ? 'bg-brand-orange text-white' : 'bg-gray-100 text-text-muted hover:bg-gray-200'
            }`}
          >
            Day {idx + 1}
          </button>
        ))}
      </div>
      {plan.days[selectedDay] && (
        <Card className="p-5">
          {photo && <img className="w-full h-40 object-cover rounded-card mb-3" src={photo.src} alt={photo.alt} />}
          <h5 className="font-bold text-sm mb-2">{plan.days[selectedDay].name || plan.days[selectedDay].title || `Day ${selectedDay + 1}`}</h5>
          <p className="text-xs text-text-muted leading-relaxed">
            {plan.days[selectedDay].passage || plan.days[selectedDay].experience || plan.days[selectedDay].summary || 'Grounded itinerary details will be confirmed by our travel team.'}
          </p>
        </Card>
      )}
      {map && <div data-component-type="InteractiveMap">
        <RouteMap value={{ ...map, selected: selectedDay }} onSelectDay={setSelectedDay} busy={false} />
      </div>}
    </div>
  );
}

function UIComponentRenderer({ component, enquiryReference, navigate, tours, setActiveTour, setWorkspacePanel, onSend }) {
  if (!component) return null;

  if (component.type === 'CancellationPreview') {
    return (
      <div className="p-3 bg-white border border-border rounded-card space-y-2 text-xs">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-text-muted">{component.policy_title}</p>
        <p className="font-semibold text-sm">{component.tour_title}</p>
        <p className="text-text-muted">{component.terms}</p>
        <p>Paid: <strong>{component.paid_amount}</strong> · Estimated simulated refund: <strong>{component.refund_amount}</strong></p>
        {component.requires_confirmation && onSend && (
          <div className="flex gap-2 pt-1">
            <Button
              variant="primary"
              size="sm"
              className="text-xs py-1 px-3"
              onClick={() => onSend(JSON.stringify({ type: 'CONFIRM_CANCELLATION', payload: { targetId: component.target_id } }))}
            >
              Confirm cancellation
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="text-xs py-1 px-3"
              onClick={() => onSend(JSON.stringify({ type: 'DECLINE_CANCELLATION', payload: {} }))}
            >
              Keep booking
            </Button>
          </div>
        )}
      </div>
    );
  }

  if (component.type === 'CancellationStatus') {
    return (
      <div className="p-3 bg-white border border-border rounded-card space-y-1 text-xs">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-text-muted">Cancellation status · {component.status}</p>
        <p>{component.summary}</p>
        {component.refund_status !== 'none' && (
          <p>Simulated refund: <strong>{component.refund_amount}</strong> ({component.refund_status})</p>
        )}
      </div>
    );
  }

  if (component.type === 'TourCard') {
    const tour = tours.find(t => t.id === component.id || t.slug === component.id) || {
      id: component.id,
      title: component.title,
      duration: component.duration,
      start: component.start,
      category: component.category,
      imgClass: 'tour-img-1',
    };
    return (
      <div 
        data-tour-id={tour.id}
        className="p-3 bg-white border border-border rounded-card hover:border-brand-orange space-y-2"
      >
        <div 
          className="flex items-center gap-3 cursor-pointer"
          onClick={() => { setActiveTour(tour); setWorkspacePanel('tour-detail'); }}
        >
          <div className={`w-10 h-10 rounded-lg ${tour.imgClass || 'tour-img-1'} flex-shrink-0`} />
          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold truncate">{tour.title}</p>
            <p className="text-xs text-text-muted">{tour.duration} • {tour.start}</p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button 
            variant="ghost" 
            size="sm" 
            className="text-xs py-1 px-3"
            onClick={() => { setActiveTour(tour); setWorkspacePanel('traveller-picker'); }}
          >
            Explore itinerary
          </Button>
          <Button 
            variant="primary" 
            size="sm" 
            className="text-xs py-1 px-3"
            onClick={() => { setActiveTour(tour); setWorkspacePanel('tour-detail'); }}
          >
            View tour
          </Button>
        </div>
      </div>
    );
  }

  if (component.type === 'TravellerPicker') {
    return (
      <div 
        className="text-xs text-brand-teal flex items-center gap-1 cursor-pointer hover:underline"
        onClick={() => setWorkspacePanel('traveller-picker')}
      >
        <Users className="w-3.5 h-3.5" />
        <span>Traveller selector available in workspace →</span>
      </div>
    );
  }

  if (component.type === 'PriceBreakdown') {
    return (
      <div 
        className="text-xs text-brand-leaf flex items-center gap-1 cursor-pointer hover:underline"
        onClick={() => setWorkspacePanel('quote')}
      >
        <Check className="w-3.5 h-3.5" />
        <span>Quote calculated — see workspace →</span>
      </div>
    );
  }

  if (component.type === 'EnquiryNotice' && (component.public_reference || component.reference || component.enquiry)) {
    const ref = component.public_reference || component.reference || component.enquiry;
    return (
      <div className="flex items-center justify-between pt-1">
        <div 
          className="text-xs text-brand-leaf flex items-center gap-1 cursor-pointer hover:underline"
          onClick={() => navigate('/enquiry/' + ref)}
        >
          <Check className="w-3.5 h-3.5" />
          <span>{String(ref).startsWith('ENQ-') ? `Enquiry saved (${ref})` : 'Enquiry saved'}</span>
        </div>
        <Button 
          variant="secondary" 
          size="sm" 
          className="text-xs py-1 px-3"
          onClick={() => navigate('/enquiry/' + ref)}
        >
          View enquiry status
        </Button>
      </div>
    );
  }

  if (component.type === 'ItineraryDay') {
    const dayLabel = component.day != null ? `Day ${component.day}` : 'Itinerary Day';
    return (
      <div
        data-component-type="ItineraryDay"
        className="p-3 bg-white border border-border rounded-card space-y-1.5 text-xs"
      >
        <div className="flex items-center justify-between gap-2">
          <span className="font-semibold text-brand-black">
            {dayLabel}{component.title ? `: ${component.title}` : ''}
          </span>
          {component.location && (
            <span className="text-[11px] text-brand-teal font-medium">{component.location}</span>
          )}
        </div>
        {component.text && <MarkdownContent content={component.text} />}
        {Array.isArray(component.highlights) && component.highlights.length > 0 && (
          <ul className="list-disc pl-4 text-text-muted space-y-0.5">
            {component.highlights.map((h, i) => <li key={i}>{h}</li>)}
          </ul>
        )}
      </div>
    );
  }

  if (component.type === 'PolicySnippet') {
    return (
      <div
        data-component-type="PolicySnippet"
        className="p-3 bg-gray-50 border border-border rounded-card space-y-1 text-xs"
      >
        {component.title && <p className="font-semibold text-brand-black">{component.title}</p>}
        {component.text && <MarkdownContent content={component.text} />}
        {component.source && <p className="text-[11px] text-text-muted">Source: {component.source}</p>}
      </div>
    );
  }

  if (component.type === 'DestinationHighlight' || component.type === 'DestinationCard') {
    return (
      <div
        data-component-type={component.type}
        className="p-3 bg-white border border-border rounded-card space-y-1 text-xs"
      >
        <div className="flex items-center justify-between gap-2">
          <span className="font-semibold text-brand-black">{component.name || component.title || 'Destination'}</span>
          {component.region && <span className="text-[11px] text-brand-teal">{component.region}</span>}
        </div>
        {(component.summary || component.text || component.description) && (
          <MarkdownContent content={component.summary || component.text || component.description} />
        )}
      </div>
    );
  }

  if (component.type === 'StayCard' || component.type === 'ActivityCard') {
    return (
      <div
        data-component-type={component.type}
        className="p-3 bg-white border border-border rounded-card space-y-1 text-xs"
      >
        <div className="flex items-center justify-between gap-2">
          <span className="font-semibold text-brand-black">{component.name || component.title || component.type}</span>
          {component.location && <span className="text-[11px] text-text-muted">{component.location}</span>}
        </div>
        {(component.description || component.text) && (
          <MarkdownContent content={component.description || component.text} />
        )}
      </div>
    );
  }

  if (component.type === 'ComparisonPanel') {
    const items = Array.isArray(component.items) ? component.items : [];
    return (
      <div
        data-component-type="ComparisonPanel"
        className="p-3 bg-white border border-border rounded-card space-y-2 text-xs"
      >
        {component.title && <p className="font-semibold text-brand-black">{component.title}</p>}
        {items.length > 0 && (
          <div className="space-y-1.5">
            {items.map((item, idx) => (
              <div key={idx} className="p-2 rounded bg-gray-50 border border-border">
                <p className="font-medium text-brand-black">{item.title || item.name || `Option ${idx + 1}`}</p>
                {item.summary && <p className="text-text-muted mt-0.5">{item.summary}</p>}
              </div>
            ))}
          </div>
        )}
        {component.text && <MarkdownContent content={component.text} />}
      </div>
    );
  }

  if (component.type === 'ConfirmationPanel') {
    const displayRef = component.reference || enquiryReference;
    return (
      <div
        data-component-type="ConfirmationPanel"
        className="p-3 bg-brand-leaf/10 border border-brand-leaf/30 rounded-card space-y-1 text-xs"
      >
        <div className="flex items-center gap-1.5 font-semibold text-brand-leaf">
          <Check className="w-3.5 h-3.5" />
          <span>{component.heading || component.title || 'Quote & enquiry saved'}</span>
        </div>
        {displayRef && <p className="font-mono text-brand-black">Enquiry ref: {displayRef}</p>}
        {component.text && <MarkdownContent content={component.text} />}
      </div>
    );
  }

  if (component.type === 'SourceReference') {
    return (
      <div
        data-component-type="SourceReference"
        className="text-[11px] text-text-muted flex items-center gap-1.5"
      >
        <FileText className="w-3 h-3 text-brand-teal flex-shrink-0" />
        <span>{component.label || component.title || component.source || 'Verified Ceylon Compass source'}</span>
      </div>
    );
  }

  if (component.type === 'JourneyPlan') {
    const days = Array.isArray(component.days) ? component.days : [];
    return (
      <div
        data-component-type="JourneyPlan"
        className="p-3 bg-white border border-border rounded-card space-y-2 text-xs"
      >
        {component.title && <p className="font-semibold text-brand-black">{component.title}</p>}
        {component.text && <MarkdownContent content={component.text} />}
        {days.length > 0 && (
          <div className="space-y-1">
            {days.map((d, idx) => {
              const dayTitle = d.name || d.title || `Stop ${idx + 1}`;
              const dayDesc = d.passage || d.experience || d.summary || 'Grounded itinerary details in workspace.';
              const shortDesc = dayDesc.length > 140 ? `${dayDesc.slice(0, 137)}...` : dayDesc;
              return (
                <div key={idx} className="text-text-muted">
                  <span className="font-medium text-brand-black">Day {d.day ?? idx + 1} — {dayTitle}:</span> {shortDesc}
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  }

  if (component.type === 'BookingForm') {
    return (
      <div
        data-component-type="BookingForm"
        className="text-xs text-brand-orange flex items-center gap-1 cursor-pointer hover:underline"
        onClick={() => setWorkspacePanel('booking')}
      >
        <Calendar className="w-3.5 h-3.5" />
        <span>Booking & contact form available in workspace →</span>
      </div>
    );
  }

  return null;
}

// ============ ABOUT PAGE ============
function AboutPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
      <h1 className="text-xl font-bold mb-6">About Ceylon Compass Holidays</h1>
      <div className="prose max-w-none space-y-6 text-text-muted leading-relaxed">
        <p>Ceylon Compass Holidays is a Sri Lankan destination management company specialising in private tours, day trips, cultural experiences, wildlife adventures and multi-day travel packages.</p>
        <p>We believe every journey should be personal. Whether you're climbing Sigiriya at sunrise, spotting elephants in Minneriya, or watching whales off the coast of Mirissa, we craft experiences that connect you with the heart of Sri Lanka.</p>
        <p>Our AI travel companion, Mira, helps you discover tours, understand itineraries and request verified quotes. Combined with our local expertise, we ensure every trip is thoughtfully planned and reliably delivered.</p>
        <h2 className="text-md font-semibold text-brand-black">What we offer</h2>
        <ul className="list-disc pl-5 space-y-2">
          <li>Private day tours from major cities</li>
          <li>Multi-day cultural and scenic round trips</li>
          <li>Custom itinerary planning</li>
          <li>Verified, transparent pricing</li>
          <li>Local guides and drivers</li>
          <li>AI-assisted trip planning with Mira</li>
        </ul>
        <h2 className="text-md font-semibold text-brand-black">Our commitment</h2>
        <p>We only publish verified tour information. Prices are calculated through our deterministic quoting system — never estimated or invented. When rates are unavailable, we connect you directly with our team for a personal response.</p>
      </div>
    </div>
  );
}

// ============ POLICIES PAGE ============
function PoliciesPage({ navigate }) {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <h1 className="text-xl font-bold mb-6">Policies</h1>
      <div className="space-y-3">
        {POLICIES.map(p => (
          <Card key={p.slug} className="p-5 cursor-pointer hover:border-brand-orange" onClick={() => navigate(`/policies/${p.slug}`)}>
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-sm">{p.title}</h3>
              <ArrowRight className="w-4 h-4 text-text-muted" />
            </div>
          </Card>
        ))}
      </div>
    </div>
  );
}

function PolicyDetailPage({ navigate, slug }) {
  const content = {
    'booking-payment': {
      title: 'Booking & Payment Policy',
      body: [
        { heading: 'Payment terms', text: 'Day and city tours require full payment at the time of booking. Multi-day tours and stays require a 25% deposit to confirm, with the balance due at least 30 days before departure.' },
        { heading: 'Late bookings', text: 'If booking within 30 days of departure, full payment is required regardless of tour type.' },
        { heading: 'Payment methods', text: 'We accept bank transfer and major credit cards. All prices are quoted in USD unless otherwise stated.' },
      ]
    },
    'cancellation': {
      title: 'Cancellation Policy',
      body: [
        { heading: 'Day and city tours', text: 'Free cancellation at least 48 hours before the scheduled start time. Cancellations within 48 hours incur a 50% charge.' },
        { heading: 'Multi-day tours', text: 'More than 30 days before departure: full refund minus processing fee. 15–30 days: 50% refund. Less than 15 days: no refund.' },
        { heading: 'Custom itineraries', text: 'Cancellation terms will be specified in your booking confirmation based on the arrangements made.' },
      ]
    },
    'children-infants': {
      title: 'Children & Infants Policy',
      body: [
        { heading: 'Infants (under 2 years)', text: 'Infants travel free when sharing existing bedding and not occupying a separate seat in vehicles. They do not incur entrance fees or meal charges under standard conditions.' },
        { heading: 'Children (2–11 years)', text: 'Children in this age range receive child pricing for entrance fees and half-price meals. Child extra beds may incur additional hotel charges.' },
        { heading: 'Ages 12 and above', text: 'Travellers aged 12 and above are priced at adult rates for all components.' },
      ]
    },
    'privacy': {
      title: 'Privacy Policy',
      body: [
        { heading: 'Data collection', text: 'We collect only the information necessary to process your enquiry or booking, including name, email, travel preferences and group details.' },
        { heading: 'AI interactions', text: 'Conversations with Mira are processed to assist your trip planning. Personal data is not used for purposes beyond providing our travel services.' },
        { heading: 'Data security', text: 'All personal information is stored securely and is not shared with third parties except as required to deliver your booking.' },
      ]
    },
    'terms': {
      title: 'Terms of Service',
      body: [
        { heading: 'Service description', text: 'Ceylon Compass Holidays provides travel arrangement services including tour booking, itinerary planning and ground operations in Sri Lanka.' },
        { heading: 'Pricing', text: 'All prices are subject to availability and confirmation. Quotes are valid for 48 hours unless otherwise stated. The final booking price is confirmed through our verified quoting system.' },
        { heading: 'Liability', text: 'While we take every care in planning your trip, we are not liable for losses due to circumstances beyond our control including weather, political events or force majeure.' },
      ]
    },
  };

  const data = content[slug];
  if (!data) {
    return (
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-24 text-center">
        <h1 className="text-xl font-bold mb-4">Policy not found</h1>
        <Button onClick={() => navigate('/policies')}>Back to policies</Button>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="flex items-center gap-2 text-sm text-text-muted mb-6">
        <button onClick={() => navigate('/policies')} className="hover:text-brand-black cursor-pointer">Policies</button>
        <ChevronRight className="w-4 h-4" />
        <span className="text-brand-black font-medium">{data.title}</span>
      </div>
      <h1 className="text-xl font-bold mb-8">{data.title}</h1>
      <div className="space-y-8">
        {data.body.map((section, i) => (
          <div key={i}>
            <h2 className="font-semibold text-md mb-2">{section.heading}</h2>
            <p className="text-text-muted leading-relaxed">{section.text}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

// ============ EXPLORE PAGE ============
function ExplorePage({ navigate }) {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <div className="mb-8">
        <h1 className="text-xl font-bold mb-2">Explore Sri Lanka</h1>
        <p className="text-text-muted">Discover experiences by travel style.</p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {TRAVEL_STYLES.map(style => {
          const Icon = style.icon;
          return (
            <Card key={style.title} className="p-8 text-center cursor-pointer hover:border-brand-orange" onClick={() => navigate('/tours')}>
              <div className={`w-16 h-16 rounded-full bg-${style.color}/10 flex items-center justify-center mx-auto mb-4`}>
                <Icon className={`w-8 h-8 text-${style.color}`} />
              </div>
              <h3 className="font-semibold text-md mb-2">{style.title}</h3>
              <p className="text-sm text-text-muted">{style.description}</p>
            </Card>
          );
        })}
      </div>
    </div>
  );
}

// ============ ENQUIRY PAGE ============
function EnquiryPage({ navigate, reference, tours = [] }) {
  const [enquiry, setEnquiry] = useState(null);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setErrorMsg('');
    (async () => {
      try {
        const res = await fetch('/api/enquiries/' + encodeURIComponent(reference));
        if (res.ok) {
          const data = await res.json();
          if (mounted) setEnquiry(data);
        } else {
          const errData = await res.json().catch(() => ({}));
          if (mounted) {
            setEnquiry(null);
            setErrorMsg(
              res.status === 404
                ? 'We could not find an enquiry matching this reference.'
                : errData.detail || 'Unable to load this enquiry right now.'
            );
          }
        }
      } catch {
        if (mounted) setErrorMsg('Unable to reach the server to load this enquiry.');
      }
      if (mounted) setLoading(false);
    })();
    return () => { mounted = false; };
  }, [reference]);

  if (loading) {
    return (
      <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-16 text-center">
        <Loader2 className="w-8 h-8 animate-spin text-brand-orange mx-auto mb-4" />
        <p className="text-sm text-text-muted">Loading enquiry details...</p>
      </div>
    );
  }

  if (!enquiry) {
    return (
      <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-16 text-center">
        <div className="w-16 h-16 rounded-full bg-red-50 flex items-center justify-center mx-auto mb-6">
          <AlertCircle className="w-8 h-8 text-red-600" />
        </div>
        <h1 className="text-xl font-bold mb-3">Enquiry not found</h1>
        <p className="text-text-muted mb-6">{errorMsg || 'This enquiry reference could not be retrieved.'}</p>
        <p className="text-xs font-mono text-text-muted mb-6">Reference: {reference}</p>
        <div className="flex justify-center gap-3">
          <Button variant="primary" onClick={() => navigate('/mira')}>Plan with Mira</Button>
          <Button variant="secondary" onClick={() => navigate('/')}>Back to home</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8 py-16 text-center">
      <div className="w-16 h-16 rounded-full bg-brand-leaf/10 flex items-center justify-center mx-auto mb-6">
        <Check className="w-8 h-8 text-brand-leaf" />
      </div>
      <h1 className="text-xl font-bold mb-3">Enquiry received</h1>
      <p className="text-text-muted mb-6">Thank you for your enquiry. Your saved journey details are available to our travel team for review.</p>
      
      <div className="bg-gray-50 rounded-card p-6 mb-8 text-left max-w-md mx-auto space-y-3">
        <div>
          <p className="text-xs text-text-muted mb-1">Reference number</p>
          <p className="text-md font-mono font-bold">{enquiry.reference || reference}</p>
        </div>
        {enquiry.tour_name && (
          <div>
            <p className="text-xs text-text-muted mb-1">Journey</p>
            <p className="text-sm font-semibold">{enquiry.tour_name}{enquiry.travel_date ? ` • ${enquiry.travel_date}` : ''}</p>
          </div>
        )}
        {enquiry.adults != null && (
          <div>
            <p className="text-xs text-text-muted mb-1">Travellers</p>
            <p className="text-sm font-medium">
              {enquiry.adults} adult{Number(enquiry.adults) === 1 ? '' : 's'}
              {enquiry.children_count ? `, ${enquiry.children_count} child${enquiry.children_count === 1 ? '' : 'ren'}` : ''}
            </p>
          </div>
        )}
        {enquiry.human_reason && (
          <div>
            <p className="text-xs text-text-muted mb-1">Details</p>
            <p className="text-sm text-text-primary">{enquiry.human_reason}</p>
          </div>
        )}
        {enquiry.created && (
          <div>
            <p className="text-xs text-text-muted mb-1">Submitted</p>
            <p className="text-xs text-text-primary">
              {new Date(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(String(enquiry.created)) ? String(enquiry.created).replace(' ', 'T') + 'Z' : enquiry.created).toLocaleString()}
            </p>
          </div>
        )}
        <div>
          <p className="text-xs text-text-muted mb-1">Enquiry Status</p>
          <span className="inline-block px-2.5 py-1 rounded-pill bg-brand-leaf/10 text-brand-leaf text-xs font-semibold capitalize">
            Status: {enquiry.status}
          </span>
        </div>
        {enquiry.quoted_total_usd != null && (
          <div className="pt-2 border-t border-border">
            <p className="text-xs text-text-muted mb-1">Verified Quotation</p>
            <p className="text-sm font-bold text-brand-black">
              USD {Number(enquiry.quoted_total_usd).toLocaleString()}
              {enquiry.quoted_deposit_usd != null ? ` (Deposit: USD ${Number(enquiry.quoted_deposit_usd).toLocaleString()})` : ''}
            </p>
          </div>
        )}
        {enquiry.mock_booking_status && (
          <div>
            <p className="text-xs text-text-muted mb-1">Simulation Status</p>
            <span className="inline-block px-2.5 py-1 rounded-pill bg-brand-teal/10 text-brand-teal text-xs font-semibold">
              Demo booking: {enquiry.mock_booking_status === 'confirmed' ? 'Confirmed' : enquiry.mock_booking_status}
            </span>
          </div>
        )}
      </div>

      {(() => {
        const storedOrigin = typeof sessionStorage !== 'undefined' ? sessionStorage.getItem('mira-enquiry-origin') : null;
        const safeOrigin = isSafeInternalRoute(storedOrigin) && storedOrigin !== '/profile' ? storedOrigin : null;
        const matchedTour = (tours || []).find((t) => t.id === enquiry.tour_id);
        const returnRoute = safeOrigin || (matchedTour && !enquiry.trip_id ? `/tours/${matchedTour.slug}` : '/mira');
        const primaryLabel = (enquiry.quoted_total_usd != null || returnRoute.startsWith('/tours/') || safeOrigin === '/mira')
          ? 'Back to quote'
          : 'Continue planning';
        return (
          <div className="flex flex-wrap justify-center gap-3">
            <Button
              variant="primary"
              onClick={() => {
                if (enquiry.trip_id && returnRoute === '/mira') {
                  sessionStorage.setItem('mira-workspace-trip', enquiry.trip_id);
                  localStorage.setItem('mira-workspace-trip', enquiry.trip_id);
                }
                navigate(returnRoute);
              }}
            >
              {primaryLabel}
            </Button>
            <Button variant="secondary" onClick={() => navigate('/profile')}>My journeys</Button>
          </div>
        );
      })()}
    </div>
  );
}

// ============ AUTH SPLIT LAYOUT ============
function AuthSplitLayout({
  children,
  imageSrc,
  imageAlt,
  eyebrow = "CEYLON COMPASS HOLIDAYS",
  headline,
  subtext,
  cardClassName = "md:min-h-[580px] lg:min-h-[584px]",
  navigate,
}) {
  return (
    <div className="min-h-screen flex justify-center items-center py-10 px-4 sm:px-6 lg:px-8 bg-[#F3EEE6]">
      {/* Outer Floating Card Container */}
      <div
        className={`w-full max-w-[980px] bg-white rounded-[22px] border border-[#E0D9CE] shadow-[0_20px_50px_-12px_rgba(20,20,20,0.13),0_4px_16px_rgba(20,20,20,0.03)] overflow-hidden flex flex-col md:flex-row ${cardClassName}`}
      >
        {/* Left Visual Storytelling Panel (Desktop / Tablet) */}
        <div className="relative hidden md:flex md:w-[48%] lg:w-[50%] flex-col justify-between p-6 sm:p-8 lg:p-9 overflow-hidden bg-[#111111]">
          {/* Photographic Background */}
          <img
            src={imageSrc}
            alt={imageAlt}
            className="absolute inset-0 w-full h-full object-cover object-center select-none"
            loading="eager"
          />

          {/* Subtle Dark Editorial Multi-stop Gradient Overlay */}
          <div className="absolute inset-0 bg-gradient-to-t from-black/95 via-black/45 to-black/30 pointer-events-none" />

          {/* Top Brand Badge */}
          <div className="relative z-10 flex items-center justify-between">
            <button
              onClick={() => navigate('/')}
              className="inline-flex items-center gap-2 group focus:outline-none focus-visible:ring-2 focus-visible:ring-[#F26B1D] rounded-full cursor-pointer text-left"
              aria-label="Ceylon Compass Holidays — home"
            >
              <div className="w-8 h-8 rounded-full bg-white/15 backdrop-blur-md border border-white/20 flex items-center justify-center group-hover:bg-white/25 transition-colors duration-150">
                <Sparkles className="w-3.5 h-3.5 text-[#F26B1D]" />
              </div>
              <span className="flex flex-col text-white">
                <span className="text-[12px] font-bold tracking-[0.16em] uppercase leading-none">Ceylon Compass</span>
                <span className="text-[9.5px] text-white/70 tracking-[0.25em] uppercase font-medium mt-0.5">Holidays</span>
              </span>
            </button>

            <span className="hidden lg:inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[10.5px] font-medium tracking-wider uppercase bg-white/15 backdrop-blur-md text-white/90 border border-white/20">
              ✦ Curated Travel
            </span>
          </div>

          {/* Bottom Editorial Content */}
          <div className="relative z-10 space-y-3 pt-8">
            <p className="eyebrow text-[10.5px] font-semibold tracking-[0.22em] text-[#F26B1D] uppercase">
              {eyebrow}
            </p>
            <h2 className="text-[25px] sm:text-[28px] lg:text-[30px] font-bold text-white tracking-[-0.03em] leading-[1.15]">
              {headline}
            </h2>
            <p className="text-[13px] text-white/85 leading-relaxed max-w-[380px]">
              {subtext}
            </p>

            {/* Subtle Brand Feature Markers */}
            <div className="pt-1 flex flex-wrap items-center gap-2.5 text-[11.5px] text-white/80 font-normal">
              <span className="inline-flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-[#F26B1D]" /> Verified rates
              </span>
              <span className="text-white/30">•</span>
              <span className="inline-flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-[#14837B]" /> Private journeys
              </span>
              <span className="text-white/30">•</span>
              <span className="inline-flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-[#F5B700]" /> Mira AI Concierge
              </span>
            </div>
          </div>
        </div>

        {/* Mobile Header Visual Banner (<md) */}
        <div className="relative w-full h-[140px] p-4.5 flex flex-col justify-between overflow-hidden md:hidden bg-[#111111]">
          <img
            src={imageSrc}
            alt={imageAlt}
            className="absolute inset-0 w-full h-full object-cover object-center select-none"
            loading="eager"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/50 to-black/35 pointer-events-none" />

          <div className="relative z-10 flex items-center justify-between">
            <button onClick={() => navigate('/')} className="inline-flex items-center gap-2 text-left" aria-label="Ceylon Compass Holidays">
              <Sparkles className="w-4 h-4 text-[#F26B1D]" />
              <span className="text-[12px] font-bold tracking-[0.16em] uppercase text-white">Ceylon Compass</span>
            </button>
            <span className="text-[10px] uppercase tracking-wider text-white/80 bg-white/10 px-2 py-0.5 rounded-full border border-white/15">
              Holidays
            </span>
          </div>

          <div className="relative z-10">
            <p className="text-[16px] font-bold text-white tracking-[-0.02em] leading-tight">
              {headline}
            </p>
          </div>
        </div>

        {/* Right Form Panel */}
        <div className="w-full md:w-[52%] lg:w-[50%] flex flex-col justify-center p-6 sm:p-7 lg:p-8 bg-white">
          <div className="w-full max-w-[370px] mx-auto">
            {children}
          </div>
        </div>
      </div>
    </div>
  );
}

// ============ LOGIN PAGE ============
function LoginPage({ navigate }) {
  const { user, login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [remember, setRemember] = useState(true);
  const [status, setStatus] = useState('');
  const [busy, setBusy] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setStatus('');

    try {
      const res = await login(email, password, remember);
      setStatus('Signed in successfully. Redirecting…');
      setTimeout(() => {
        if (['staff', 'editor', 'approver', 'admin'].includes(res.role)) {
          navigate('/staff');
        } else {
          navigate('/profile');
        }
      }, 400);
    } catch (err) {
      setStatus(err.message || 'Failed to sign in. Please verify your credentials.');
    } finally {
      setBusy(false);
    }
  };

  const isSuccess = status.includes('successfully');

  return (
    <AuthSplitLayout
      imageSrc={photos.sigiriyaAerial.src}
      imageAlt={photos.sigiriyaAerial.alt}
      eyebrow="CEYLON COMPASS HOLIDAYS"
      headline="Your next story begins in Sri Lanka."
      subtext="Discover remarkable places, thoughtful journeys, and experiences designed around you."
      cardClassName="md:min-h-[580px] lg:min-h-[584px]"
      navigate={navigate}
    >
      <div className="text-left flex flex-col justify-center py-2 sm:py-3">
        <h1 className="text-[24px] sm:text-[26px] font-bold text-[#111111] tracking-[-0.03em] leading-tight">
          Welcome back
        </h1>
        <p className="text-[13px] text-[#5F5F5F] mt-1.5 leading-normal">
          Sign in to continue your Sri Lanka journey.
        </p>

        {status && (
          <div
            role={isSuccess ? 'status' : 'alert'}
            className={`my-3.5 p-3 rounded-[8px] text-[12.5px] font-medium flex items-start gap-2.5 transition-all duration-150 ${
              isSuccess
                ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                : 'bg-red-50 text-red-800 border border-red-200'
            }`}
          >
            {isSuccess ? (
              <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
            ) : (
              <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
            )}
            <div className="flex-1">{status}</div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-5 space-y-3.5">
          <div className="space-y-1 text-left">
            <label htmlFor="login-email" className="block text-[12.5px] font-semibold text-[#111111]">
              Email address <span className="text-[#F26B1D]">*</span>
            </label>
            <input
              id="login-email"
              type="email"
              required
              autoComplete="email"
              value={email}
              disabled={busy}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="traveller@example.com"
              className="w-full h-[40px] px-3 rounded-[8px] border border-[#E6E6E6] text-[13.5px] bg-white text-[#111111] placeholder:text-[#5F5F5F]/60 transition-colors duration-150 focus:outline-none focus:ring-2 focus:border-[#F26B1D] focus:ring-[#F26B1D]/20 disabled:bg-gray-50 disabled:text-gray-400"
            />
          </div>

          <div className="space-y-1 text-left">
            <div className="flex items-center justify-between">
              <label htmlFor="login-password" className="block text-[12.5px] font-semibold text-[#111111]">
                Password
              </label>
            </div>
            <div className="relative">
              <input
                id="login-password"
                type={showPassword ? 'text' : 'password'}
                required
                autoComplete="current-password"
                value={password}
                disabled={busy}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full h-[40px] pl-3 pr-10 rounded-[8px] border border-[#E6E6E6] text-[13.5px] bg-white text-[#111111] placeholder:text-[#5F5F5F]/60 transition-colors duration-150 focus:outline-none focus:ring-2 focus:border-[#F26B1D] focus:ring-[#F26B1D]/20 disabled:bg-gray-50 disabled:text-gray-400"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-[#5F5F5F] hover:text-[#111111] p-1 cursor-pointer"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <div className="pt-0.5">
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <input
                type="checkbox"
                className="w-3.5 h-3.5 rounded-[4px] border-[#E6E6E6] text-[#F26B1D] accent-[#F26B1D] focus:ring-[#F26B1D]/20 cursor-pointer"
                checked={remember}
                disabled={busy}
                onChange={(e) => setRemember(e.target.checked)}
              />
              <span className="text-[12.5px] text-[#5F5F5F]">Remember this browser for 30 days</span>
            </label>
          </div>

          <button
            type="submit"
            disabled={busy}
            className="w-full h-[43px] rounded-full bg-[#F26B1D] hover:bg-[#d95a12] active:bg-[#c44f0e] text-white text-[13.5px] font-semibold flex items-center justify-center gap-2 shadow-xs transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#F26B1D] focus-visible:ring-offset-2 disabled:opacity-70 disabled:cursor-not-allowed mt-2.5 cursor-pointer"
          >
            {busy ? (
              <span className="flex items-center gap-2">
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Signing in…
              </span>
            ) : (
              <span>Sign in</span>
            )}
          </button>
        </form>

        <p className="text-[12.5px] text-[#5F5F5F] text-center mt-5">
          New to Ceylon Compass?{' '}
          <button
            onClick={() => navigate('/register')}
            className="font-semibold text-[#F26B1D] hover:underline focus:outline-none cursor-pointer"
          >
            Create an account
          </button>
        </p>

        <div className="mt-6 pt-3.5 border-t border-[#E6E6E6] text-[11px] text-[#5F5F5F] text-center leading-normal">
          Staff, Approvers, and Admins can sign in here to access the Staff Console.
        </div>
      </div>
    </AuthSplitLayout>
  );
}

// ============ REGISTER PAGE ============
function RegisterPage({ navigate }) {
  const { user, register } = useAuth();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [phone, setPhone] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [status, setStatus] = useState('');
  const [busy, setBusy] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (password.length < 8) {
      setStatus('Password must be at least 8 characters.');
      return;
    }
    setBusy(true);
    setStatus('');

    try {
      await register({
        full_name: fullName.trim(),
        email: email.trim(),
        password,
        phone: phone.trim(),
      });
      setStatus('Account created successfully! Preparing your notebook…');
      setTimeout(() => {
        navigate('/profile');
      }, 400);
    } catch (err) {
      setStatus(err.message || 'Registration failed. Please try again.');
    } finally {
      setBusy(false);
    }
  };

  const isSuccess = status.includes('successfully');

  return (
    <AuthSplitLayout
      imageSrc={photos.nineArchesTrain.src}
      imageAlt={photos.nineArchesTrain.alt}
      eyebrow="CEYLON COMPASS HOLIDAYS"
      headline="Your bespoke Sri Lanka journey awaits."
      subtext="Personalised itineraries, verified transparent rates, and dedicated human concierge support every step of the way."
      cardClassName="md:min-h-[580px] lg:min-h-[584px]"
      navigate={navigate}
    >
      <div className="text-left">
        <h1 className="text-[23px] sm:text-[25px] font-bold text-[#111111] tracking-[-0.03em] leading-tight">
          Create your account
        </h1>
        <p className="text-[13px] text-[#5F5F5F] mt-1 leading-normal">
          Keep your journeys, saved quotes, and travel preferences together.
        </p>

        {status && (
          <div
            role={isSuccess ? 'status' : 'alert'}
            className={`my-3 p-3 rounded-[8px] text-[12.5px] font-medium flex items-start gap-2.5 transition-all duration-150 ${
              isSuccess
                ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                : 'bg-red-50 text-red-800 border border-red-200'
            }`}
          >
            {isSuccess ? (
              <CheckCircle className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
            ) : (
              <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
            )}
            <div className="flex-1">{status}</div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-4 space-y-2.5">
          <div className="space-y-1 text-left">
            <label htmlFor="reg-fullname" className="block text-[12.5px] font-semibold text-[#111111]">
              Full name <span className="text-[#F26B1D]">*</span>
            </label>
            <input
              id="reg-fullname"
              type="text"
              required
              autoComplete="name"
              value={fullName}
              disabled={busy}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="e.g. Saman Perera"
              className="w-full h-[40px] px-3 rounded-[8px] border border-[#E6E6E6] text-[13.5px] bg-white text-[#111111] placeholder:text-[#5F5F5F]/60 transition-colors duration-150 focus:outline-none focus:ring-2 focus:border-[#F26B1D] focus:ring-[#F26B1D]/20 disabled:bg-gray-50 disabled:text-gray-400"
            />
          </div>

          <div className="space-y-1 text-left">
            <label htmlFor="reg-email" className="block text-[12.5px] font-semibold text-[#111111]">
              Email address <span className="text-[#F26B1D]">*</span>
            </label>
            <input
              id="reg-email"
              type="email"
              required
              autoComplete="email"
              value={email}
              disabled={busy}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="traveller@example.com"
              className="w-full h-[40px] px-3 rounded-[8px] border border-[#E6E6E6] text-[13.5px] bg-white text-[#111111] placeholder:text-[#5F5F5F]/60 transition-colors duration-150 focus:outline-none focus:ring-2 focus:border-[#F26B1D] focus:ring-[#F26B1D]/20 disabled:bg-gray-50 disabled:text-gray-400"
            />
          </div>

          <div className="space-y-1 text-left">
            <div className="flex items-center justify-between">
              <label htmlFor="reg-password" className="block text-[12.5px] font-semibold text-[#111111]">
                Password
              </label>
              <span className="text-[11.5px] text-[#5F5F5F]">Min. 8 characters</span>
            </div>
            <div className="relative">
              <input
                id="reg-password"
                type={showPassword ? 'text' : 'password'}
                required
                autoComplete="new-password"
                minLength={8}
                value={password}
                disabled={busy}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full h-[40px] pl-3 pr-10 rounded-[8px] border border-[#E6E6E6] text-[13.5px] bg-white text-[#111111] placeholder:text-[#5F5F5F]/60 transition-colors duration-150 focus:outline-none focus:ring-2 focus:border-[#F26B1D] focus:ring-[#F26B1D]/20 disabled:bg-gray-50 disabled:text-gray-400"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-[#5F5F5F] hover:text-[#111111] p-1 cursor-pointer"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <div className="space-y-1 text-left">
            <div className="flex items-center justify-between">
              <label htmlFor="reg-phone" className="block text-[12.5px] font-semibold text-[#111111]">
                Contact phone
              </label>
              <span className="text-[11.5px] text-[#5F5F5F]">Optional</span>
            </div>
            <input
              id="reg-phone"
              type="tel"
              autoComplete="tel"
              value={phone}
              disabled={busy}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="+94 77 123 4567"
              className="w-full h-[40px] px-3 rounded-[8px] border border-[#E6E6E6] text-[13.5px] bg-white text-[#111111] placeholder:text-[#5F5F5F]/60 transition-colors duration-150 focus:outline-none focus:ring-2 focus:border-[#F26B1D] focus:ring-[#F26B1D]/20 disabled:bg-gray-50 disabled:text-gray-400"
            />
          </div>

          <button
            type="submit"
            disabled={busy}
            className="w-full h-[42px] rounded-full bg-[#F26B1D] hover:bg-[#d95a12] active:bg-[#c44f0e] text-white text-[13.5px] font-semibold flex items-center justify-center gap-2 shadow-xs transition-colors duration-150 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#F26B1D] focus-visible:ring-offset-2 disabled:opacity-70 disabled:cursor-not-allowed mt-2 cursor-pointer"
          >
            {busy ? (
              <span className="flex items-center gap-2">
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Creating account…
              </span>
            ) : (
              <span>Create account</span>
            )}
          </button>
        </form>

        <p className="text-[12.5px] text-[#5F5F5F] text-center mt-3.5">
          Already travelling with us?{' '}
          <button
            onClick={() => navigate('/login')}
            className="font-semibold text-[#F26B1D] hover:underline focus:outline-none cursor-pointer"
          >
            Sign in
          </button>
        </p>

        <div className="mt-4 pt-3 border-t border-[#E6E6E6] text-[11px] text-[#5F5F5F] text-center leading-normal">
          By signing up, your verified quotes and trip notebooks will sync securely across your devices.
        </div>
      </div>
    </AuthSplitLayout>
  );
}

// ============ PROFILE PAGE ============
function ProfilePage({ navigate }) {
  const { user, logout, refreshUser } = useAuth();
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview'); // 'overview' | 'bookings' | 'edit' | 'password'

  // My Bookings state
  const [bookingsData, setBookingsData] = useState(null);
  const [bookingsFilter, setBookingsFilter] = useState('all');
  const [bookingsLoading, setBookingsLoading] = useState(false);
  const [bookingActionMsg, setBookingActionMsg] = useState({ type: '', text: '' });
  const [bookingBusy, setBookingBusy] = useState(false);
  const [detailBooking, setDetailBooking] = useState(null);
  const [historyBooking, setHistoryBooking] = useState(null);
  const [cancelPreview, setCancelPreview] = useState(null);

  // Edit form state
  const [fullName, setFullName] = useState('');
  const [phone, setPhone] = useState('');
  const [dietary, setDietary] = useState('none');
  const [pace, setPace] = useState('balanced');
  const [profileMsg, setProfileMsg] = useState({ type: '', text: '' });
  const [profileBusy, setProfileBusy] = useState(false);

  // Password state
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmNewPassword, setConfirmNewPassword] = useState('');
  const [pwdMsg, setPwdMsg] = useState({ type: '', text: '' });
  const [pwdBusy, setPwdBusy] = useState(false);

  useEffect(() => {
    if (!user) return;
    setFullName(user.full_name || '');
    setPhone(user.phone || '');
    setDietary(user.preferences?.dietary || 'none');
    setPace(user.preferences?.pace || 'balanced');

    let mounted = true;
    (async () => {
      try {
        const [ov, bk] = await Promise.all([
          api('/traveller/overview'),
          api(`/traveller/bookings?filter=${encodeURIComponent(bookingsFilter)}`).catch(() => null),
        ]);
        if (mounted) {
          setOverview(ov);
          if (bk) setBookingsData(bk);
        }
      } catch {}
      finally {
        if (mounted) setLoading(false);
      }
    })();
    return () => { mounted = false; };
  }, [user, bookingsFilter]);

  const reloadBookingsAndOverview = async (filterVal = bookingsFilter) => {
    setBookingsLoading(true);
    try {
      const [ov, bk] = await Promise.all([
        api('/traveller/overview'),
        api(`/traveller/bookings?filter=${encodeURIComponent(filterVal)}`),
      ]);
      setOverview(ov);
      setBookingsData(bk);
    } catch (err) {
      setBookingActionMsg({ type: 'error', text: err.message || 'Could not refresh bookings.' });
    } finally {
      setBookingsLoading(false);
    }
  };

  const handlePayBalance = async (bk) => {
    setBookingBusy(true);
    setBookingActionMsg({ type: '', text: '' });
    try {
      const idem = `pay-${bk.booking_reference}-${bk.outstanding_balance}-${Date.now()}`;
      const res = await api(`/bookings/${encodeURIComponent(bk.booking_reference)}/pay`, {
        method: 'POST',
        body: JSON.stringify({ amount: bk.outstanding_balance, scenario: 'success', idempotency_key: idem }),
      });
      setBookingActionMsg({
        type: 'success',
        text: `Simulated balance payment of USD ${res.amount} completed for ${bk.tour_name}.`,
      });
      await reloadBookingsAndOverview();
    } catch (err) {
      setBookingActionMsg({ type: 'error', text: err.message || 'Simulated payment failed.' });
    } finally {
      setBookingBusy(false);
    }
  };

  const handleOpenCancelPreview = async (bk) => {
    setBookingBusy(true);
    setBookingActionMsg({ type: '', text: '' });
    try {
      const prev = await api(`/bookings/${encodeURIComponent(bk.booking_reference)}/cancel/preview`, {
        method: 'POST',
      });
      setCancelPreview({ ...prev, tour_name: bk.tour_name, travel_date: bk.travel_date });
    } catch (err) {
      setBookingActionMsg({ type: 'error', text: err.message || 'Could not load cancellation preview.' });
    } finally {
      setBookingBusy(false);
    }
  };

  const handleConfirmCancellation = async () => {
    if (!cancelPreview) return;
    setBookingBusy(true);
    setBookingActionMsg({ type: '', text: '' });
    try {
      const res = await api(`/bookings/${encodeURIComponent(cancelPreview.booking_reference)}/cancel`, {
        method: 'POST',
        body: JSON.stringify({ reason: 'traveller_requested' }),
      });
      setCancelPreview(null);
      setBookingActionMsg({
        type: 'success',
        text: res.status === 'pending_staff'
          ? 'Cancellation submitted for specialist review.'
          : `Booking cancelled. Simulated refund: USD ${res.refund_amount} (${res.refund_status}).`,
      });
      await reloadBookingsAndOverview();
    } catch (err) {
      setBookingActionMsg({ type: 'error', text: err.message || 'Could not confirm cancellation.' });
    } finally {
      setBookingBusy(false);
    }
  };

  if (!user) {
    return (
      <div className="max-w-md mx-auto px-4 py-24 text-center">
        <Card className="p-8">
          <div className="w-12 h-12 rounded-full bg-brand-orange/10 text-brand-orange flex items-center justify-center mx-auto mb-4">
            <Lock className="w-6 h-6" />
          </div>
          <h2 className="text-lg font-bold mb-2">Sign In Required</h2>
          <p className="text-xs text-text-muted mb-6">
            Please sign in to view your travel profile, saved quotes, and private booking status.
          </p>
          <div className="flex flex-col gap-3">
            <Button variant="primary" onClick={() => navigate('/login')}>Sign In</Button>
            <Button variant="ghost" onClick={() => navigate('/register')}>Create Account</Button>
          </div>
        </Card>
      </div>
    );
  }

  const roleBadge = (role) => {
    switch (role) {
      case 'admin':
        return <span className="px-2.5 py-0.5 rounded-pill text-xs font-semibold bg-red-100 text-red-800 border border-red-200">System Administrator</span>;
      case 'approver':
        return <span className="px-2.5 py-0.5 rounded-pill text-xs font-semibold bg-blue-100 text-blue-800 border border-blue-200">Content Approver</span>;
      case 'staff':
      case 'editor':
        return <span className="px-2.5 py-0.5 rounded-pill text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-200">Staff Member</span>;
      default:
        return <span className="px-2.5 py-0.5 rounded-pill text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200">Traveller</span>;
    }
  };

  const handleProfileSave = async (e) => {
    e.preventDefault();
    setProfileMsg({ type: '', text: '' });
    setProfileBusy(true);
    try {
      await api('/auth/profile', {
        method: 'PATCH',
        body: JSON.stringify({
          full_name: fullName.trim(),
          phone: phone.trim(),
          preferences: { dietary, pace },
        }),
      });
      await refreshUser();
      setProfileMsg({ type: 'success', text: 'Profile updated successfully!' });
    } catch (err) {
      setProfileMsg({ type: 'error', text: err.message || 'Failed to update profile.' });
    } finally {
      setProfileBusy(false);
    }
  };

  const handlePasswordChange = async (e) => {
    e.preventDefault();
    setPwdMsg({ type: '', text: '' });
    if (newPassword.length < 8) {
      setPwdMsg({ type: 'error', text: 'New password must be at least 8 characters long.' });
      return;
    }
    if (newPassword !== confirmNewPassword) {
      setPwdMsg({ type: 'error', text: 'New passwords do not match.' });
      return;
    }
    setPwdBusy(true);
    try {
      await api('/auth/password', {
        method: 'POST',
        body: JSON.stringify({
          current_password: currentPassword,
          new_password: newPassword,
        }),
      });
      setCurrentPassword('');
      setNewPassword('');
      setConfirmNewPassword('');
      setPwdMsg({ type: 'success', text: 'Password changed successfully.' });
    } catch (err) {
      setPwdMsg({ type: 'error', text: err.message || 'Failed to change password.' });
    } finally {
      setPwdBusy(false);
    }
  };

  const isPrivileged = ['admin', 'approver', 'staff', 'editor'].includes(user.role);

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      {/* Header Profile Card */}
      <Card className="p-6 sm:p-8 mb-8">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-full bg-brand-orange text-white flex items-center justify-center text-xl font-bold shrink-0 shadow-sm">
              {user.full_name ? user.full_name.charAt(0).toUpperCase() : 'U'}
            </div>
            <div>
              <div className="flex items-center gap-2.5 flex-wrap">
                <h1 className="text-xl font-bold">{user.full_name}</h1>
                {roleBadge(user.role)}
              </div>
              <p className="text-xs text-text-muted mt-0.5">{user.email}</p>
              {user.phone && <p className="text-xs text-text-muted">{user.phone}</p>}
            </div>
          </div>
          <div className="flex items-center gap-2 self-stretch sm:self-auto">
            {isPrivileged && (
              <Button variant="secondary" size="sm" onClick={() => navigate('/staff')}>
                <Shield className="w-3.5 h-3.5 mr-1.5" />
                Staff Console
              </Button>
            )}
            <Button variant="ghost" size="sm" onClick={logout}>
              <LogOut className="w-3.5 h-3.5 mr-1.5" />
              Sign Out
            </Button>
          </div>
        </div>

        {/* Privileged Banner */}
        {isPrivileged && (
          <div className="mt-6 p-4 rounded-card bg-amber-50 border border-amber-200 text-amber-900 text-xs flex items-center justify-between gap-4">
            <div className="flex items-center gap-2.5">
              <Shield className="w-5 h-5 text-amber-700 shrink-0" />
              <span>
                <strong>Elevated Privileges:</strong> You are logged in with{' '}
                <span className="font-semibold uppercase">{user.role}</span> permissions.
              </span>
            </div>
            <button
              onClick={() => navigate('/staff')}
              className="text-amber-800 font-bold underline hover:text-amber-950 shrink-0 cursor-pointer"
            >
              Open Staff Portal →
            </button>
          </div>
        )}
      </Card>

      {/* Tabs */}
      <div className="flex gap-2 mb-6 border-b border-border pb-3 flex-wrap">
        <Button
          variant={activeTab === 'overview' ? 'primary' : 'ghost'}
          size="sm"
          onClick={() => setActiveTab('overview')}
        >
          My Journeys & Enquiries
        </Button>
        <Button
          variant={activeTab === 'bookings' ? 'primary' : 'ghost'}
          size="sm"
          onClick={() => setActiveTab('bookings')}
        >
          My Bookings
        </Button>
        <Button
          variant={activeTab === 'edit' ? 'primary' : 'ghost'}
          size="sm"
          onClick={() => setActiveTab('edit')}
        >
          Personal Details
        </Button>
        <Button
          variant={activeTab === 'password' ? 'primary' : 'ghost'}
          size="sm"
          onClick={() => setActiveTab('password')}
        >
          Security & Password
        </Button>
      </div>

      {/* Tab: My Bookings */}
      {activeTab === 'bookings' && (
        <div className="space-y-6">
          {/* Summary Metrics */}
          <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
            <Card className="p-4">
              <p className="text-[11px] text-text-muted mb-1">Upcoming Confirmed</p>
              <p className="text-xl font-bold text-brand-teal">{bookingsData?.summary?.upcoming_confirmed ?? 0}</p>
            </Card>
            <Card className="p-4">
              <p className="text-[11px] text-text-muted mb-1">Fully Paid</p>
              <p className="text-xl font-bold text-emerald-600">{bookingsData?.summary?.fully_paid ?? 0}</p>
            </Card>
            <Card className="p-4">
              <p className="text-[11px] text-text-muted mb-1">Outstanding Balance</p>
              <p className="text-xl font-bold text-brand-orange">USD {bookingsData?.summary?.outstanding_balance_total ?? '0'}</p>
            </Card>
            <Card className="p-4">
              <p className="text-[11px] text-text-muted mb-1">Pending Cancellation</p>
              <p className="text-xl font-bold text-amber-600">{bookingsData?.summary?.pending_cancellations ?? 0}</p>
            </Card>
            <Card className="p-4">
              <p className="text-[11px] text-text-muted mb-1">Cancelled</p>
              <p className="text-xl font-bold text-text-muted">{bookingsData?.summary?.cancelled ?? 0}</p>
            </Card>
          </div>

          {bookingActionMsg.text && (
            <div className={`p-3 rounded-card text-xs border ${bookingActionMsg.type === 'error' ? 'bg-red-50 text-red-700 border-red-200' : 'bg-emerald-50 text-emerald-800 border-emerald-200'}`}>
              {bookingActionMsg.text}
            </div>
          )}

          {/* Filter Pills */}
          <div className="flex flex-wrap gap-2">
            {[
              ['all', 'All bookings'],
              ['upcoming', 'Upcoming bookings'],
              ['outstanding', 'Payment outstanding'],
              ['completed', 'Completed journeys'],
              ['cancellation_pending', 'Cancellation pending'],
              ['cancelled', 'Cancelled bookings'],
            ].map(([val, label]) => (
              <Button
                key={val}
                variant={bookingsFilter === val ? 'primary' : 'ghost'}
                size="sm"
                onClick={() => setBookingsFilter(val)}
              >
                {label}
              </Button>
            ))}
          </div>

          {/* Booking Cards */}
          {bookingsLoading ? (
            <Card className="p-8 text-center text-xs text-text-muted">Loading bookings...</Card>
          ) : bookingsData?.bookings?.length > 0 ? (
            <div className="space-y-4">
              {bookingsData.bookings.map((bk) => {
                const totalN = Number(bk.total_amount) || 0;
                const paidN = Number(bk.paid_amount) || 0;
                const pct = totalN > 0 ? Math.min(100, Math.round((paidN / totalN) * 100)) : 100;
                const isCancelled = bk.booking_status === 'cancelled';
                const isPendingCancel = bk.booking_status === 'cancellation_pending';
                const hasBalance = Number(bk.outstanding_balance) > 0;
                const payStatusLabel = {
                  deposit_paid: 'Deposit paid',
                  partially_paid: 'Partially paid',
                  fully_paid: 'Fully paid',
                  payment_pending: 'Payment pending',
                  payment_failed: 'Payment failed',
                  simulated_refund_completed: 'Simulated refund completed',
                }[bk.payment_status] || bk.payment_status;

                return (
                  <Card key={bk.booking_reference} className="p-5 sm:p-6">
                    <div className="flex flex-col sm:flex-row gap-4">
                      {bk.tour_image && (
                        <img
                          src={bk.tour_image}
                          alt={bk.tour_name}
                          className="w-full sm:w-36 h-28 object-cover rounded-card shrink-0 border border-border"
                        />
                      )}
                      <div className="flex-1 min-w-0 space-y-3">
                        <div className="flex items-start justify-between gap-3 flex-wrap">
                          <div>
                            <div className="flex items-center gap-2 flex-wrap">
                              <h3 className="font-bold text-base text-brand-black">{bk.tour_name}</h3>
                              <span className={`px-2.5 py-0.5 rounded-pill text-[11px] font-semibold capitalize ${
                                isCancelled ? 'bg-gray-200 text-gray-700' :
                                isPendingCancel ? 'bg-amber-100 text-amber-800' :
                                'bg-brand-teal/10 text-brand-teal'
                              }`}>
                                {bk.booking_status.replace('_', ' ')}
                              </span>
                              <span className={`px-2.5 py-0.5 rounded-pill text-[11px] font-semibold ${
                                bk.payment_status === 'fully_paid' ? 'bg-emerald-100 text-emerald-800' :
                                bk.payment_status === 'simulated_refund_completed' ? 'bg-teal-100 text-teal-800' :
                                bk.payment_status === 'payment_failed' ? 'bg-red-100 text-red-700' :
                                'bg-amber-100 text-amber-800'
                              }`}>
                                {payStatusLabel}
                              </span>
                            </div>
                            <p className="text-xs text-text-muted mt-1">
                              Ref: <span className="font-mono font-semibold text-brand-black">{bk.booking_reference.slice(0, 8).toUpperCase()}</span>
                              {' • '}Travel: {bk.travel_date}
                              {bk.duration ? ` • ${bk.duration}` : ''}
                              {' • '}{bk.adults} adult{bk.adults === 1 ? '' : 's'}{bk.children ? `, ${bk.children} child${bk.children === 1 ? '' : 'ren'}` : ''}
                            </p>
                          </div>
                          <div className="text-right">
                            <p className="text-[11px] text-text-muted">Total Price</p>
                            <p className="text-base font-bold text-brand-black">{bk.currency} {bk.total_amount}</p>
                          </div>
                        </div>

                        {/* Payment Progress */}
                        <div className="bg-gray-50 border border-border rounded-card p-3 space-y-2 text-xs">
                          <div className="flex items-center justify-between gap-2 flex-wrap">
                            <span>Paid (simulated): <strong className="text-emerald-700">{bk.currency} {bk.paid_amount}</strong></span>
                            <span>Remaining balance: <strong className={hasBalance && !isCancelled ? 'text-brand-orange' : 'text-text-muted'}>{bk.currency} {bk.outstanding_balance}</strong></span>
                          </div>
                          <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                            <div className="h-full bg-brand-teal transition-all" style={{ width: `${pct}%` }} />
                          </div>
                          {bk.balance_due_date && (
                            <p className="text-[11px] text-text-muted">{bk.payment_terms}: due by <strong>{bk.balance_due_date}</strong></p>
                          )}
                          {bk.refund_status && bk.refund_status !== 'none' && (
                            <p className="text-[11px] text-brand-teal font-medium">
                              Refund status: {bk.refund_status.replace('_', ' ')} {bk.refund_amount ? `(USD ${bk.refund_amount})` : ''}
                            </p>
                          )}
                        </div>

                        {/* Contextual Actions */}
                        <div className="flex flex-wrap gap-2 pt-1">
                          <Button variant="ghost" size="sm" onClick={() => setDetailBooking(bk)}>View details</Button>
                          <Button variant="ghost" size="sm" onClick={() => setHistoryBooking(bk)}>Payment history</Button>
                          {bk.trip_id && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                sessionStorage.setItem('mira-workspace-trip', bk.trip_id);
                                localStorage.setItem('mira-workspace-trip', bk.trip_id);
                                navigate('/mira');
                              }}
                            >
                              Resume in Mira
                            </Button>
                          )}
                          {bk.booking_status === 'confirmed' && hasBalance && (
                            <Button variant="primary" size="sm" disabled={bookingBusy} onClick={() => handlePayBalance(bk)}>
                              Pay remaining balance (USD {bk.outstanding_balance})
                            </Button>
                          )}
                          {bk.booking_status === 'confirmed' && (
                            <Button variant="ghost" size="sm" disabled={bookingBusy} onClick={() => handleOpenCancelPreview(bk)}>
                              Cancel booking
                            </Button>
                          )}
                          {bk.enquiry_reference && (
                            <Button variant="ghost" size="sm" onClick={() => navigate('/enquiry/' + bk.enquiry_reference)}>
                              Contact specialist
                            </Button>
                          )}
                        </div>
                      </div>
                    </div>
                  </Card>
                );
              })}
            </div>
          ) : (
            <Card className="p-8 text-center text-xs text-text-muted">
              <p>No bookings match this filter yet.</p>
              <button onClick={() => navigate('/mira')} className="mt-2 text-brand-orange font-semibold hover:underline cursor-pointer">
                Explore tours with Mira →
              </button>
            </Card>
          )}

          {/* Modal: Booking Details */}
          {detailBooking && (
            <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4" role="dialog" aria-modal="true">
              <Card className="max-w-lg w-full p-6 space-y-3 bg-white">
                <h3 className="font-bold text-base">{detailBooking.tour_name}</h3>
                <p className="text-xs text-text-muted">
                  Reference: {detailBooking.booking_reference} • Date: {detailBooking.travel_date} • Status: {detailBooking.booking_status}
                </p>
                <p className="text-xs">Destinations: {(detailBooking.destinations || []).join(', ') || 'See itinerary'}</p>
                <p className="text-xs">Total: USD {detailBooking.total_amount} • Paid (simulated): USD {detailBooking.paid_amount} • Outstanding: USD {detailBooking.outstanding_balance}</p>
                {detailBooking.refund_status && detailBooking.refund_status !== 'none' && (
                  <p className="text-xs text-brand-teal">Refund: USD {detailBooking.refund_amount || '0'} ({detailBooking.refund_status})</p>
                )}
                <div className="flex justify-end pt-2">
                  <Button variant="primary" size="sm" onClick={() => setDetailBooking(null)}>Close</Button>
                </div>
              </Card>
            </div>
          )}

          {/* Modal: Payment History */}
          {historyBooking && (
            <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4" role="dialog" aria-modal="true">
              <Card className="max-w-lg w-full p-6 space-y-3 bg-white">
                <h3 className="font-bold text-base">Simulated Payment History</h3>
                <p className="text-xs text-text-muted">{historyBooking.tour_name} • All payments are simulated.</p>
                <div className="space-y-2 max-h-60 overflow-y-auto">
                  {(historyBooking.payments || []).length > 0 ? historyBooking.payments.map((p) => (
                    <div key={p.id} className="flex items-center justify-between text-xs p-2.5 rounded-card bg-gray-50 border border-border">
                      <div>
                        <span className="font-semibold capitalize">{p.payment_type}</span>
                        <span className="text-text-muted ml-2">({p.status})</span>
                      </div>
                      <span className="font-mono font-bold">{p.currency} {p.amount}</span>
                    </div>
                  )) : (
                    <p className="text-xs text-text-muted">Initial simulated deposit USD {historyBooking.paid_amount} recorded.</p>
                  )}
                </div>
                <div className="flex justify-end pt-2">
                  <Button variant="primary" size="sm" onClick={() => setHistoryBooking(null)}>Close</Button>
                </div>
              </Card>
            </div>
          )}

          {/* Modal: HITL Cancellation Preview */}
          {cancelPreview && (
            <div className="fixed inset-0 z-50 bg-black/40 flex items-center justify-center p-4" role="dialog" aria-modal="true">
              <Card className="max-w-lg w-full p-6 space-y-4 bg-white">
                <h3 className="font-bold text-base">Confirm Booking Cancellation</h3>
                <p className="text-xs text-text-muted">{cancelPreview.tour_name} • Travel date: {cancelPreview.travel_date}</p>
                <div className="p-3 rounded-card bg-amber-50 border border-amber-200 text-xs space-y-1.5">
                  <p><strong>Policy:</strong> {cancelPreview.policy_version}</p>
                  <p>{cancelPreview.terms}</p>
                  <p><strong>Recorded payment (simulated):</strong> USD {cancelPreview.paid_amount}</p>
                  <p><strong>Eligible simulated refund:</strong> {cancelPreview.escalate_to_staff ? 'Specialist review required' : `USD ${cancelPreview.refund_amount}`}</p>
                </div>
                <div className="flex justify-end gap-2">
                  <Button variant="ghost" size="sm" disabled={bookingBusy} onClick={() => setCancelPreview(null)}>
                    Keep Booking
                  </Button>
                  <Button variant="primary" size="sm" disabled={bookingBusy} onClick={handleConfirmCancellation}>
                    Confirm Cancellation
                  </Button>
                </div>
              </Card>
            </div>
          )}
        </div>
      )}

      {/* Tab: Overview */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Card className="p-5">
              <p className="text-xs text-text-muted mb-1">Total Saved Quotes</p>
              <p className="text-2xl font-bold text-brand-orange">{overview?.total_quotes ?? 0}</p>
            </Card>
            <Card className="p-5">
              <p className="text-xs text-text-muted mb-1">Active Enquiries</p>
              <p className="text-2xl font-bold text-brand-teal">{overview?.active_enquiries ?? overview?.total_enquiries ?? 0}</p>
            </Card>
            <Card className="p-5">
              <p className="text-xs text-text-muted mb-1">Saved Journeys</p>
              <p className="text-2xl font-bold text-brand-leaf">{overview?.total_trips ?? overview?.trips?.length ?? 0}</p>
            </Card>
          </div>

          {/* Last Quote */}
          {overview?.last_quote && (
            <Card className="p-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <span className="text-[11px] font-semibold text-brand-orange uppercase tracking-wider">Latest Quotation</span>
                  <h3 className="font-bold text-md mt-0.5">{overview.last_quote.title}</h3>
                </div>
                <span className="text-lg font-bold text-brand-orange">
                  USD {overview.last_quote.total}
                </span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs py-3 border-y border-border">
                <div>
                  <span className="text-text-muted block">Travel Date</span>
                  <span className="font-medium">{overview.last_quote.date || 'Flexible'}</span>
                </div>
                <div>
                  <span className="text-text-muted block">Travellers</span>
                  <span className="font-medium">
                    {overview.last_quote.adults} Adults
                    {overview.last_quote.children ? `, ${overview.last_quote.children} Children` : ''}
                  </span>
                </div>
                <div>
                  <span className="text-text-muted block">Deposit Required</span>
                  <span className="font-medium">USD {overview.last_quote.deposit}</span>
                </div>
                <div>
                  <span className="text-text-muted block">Rate Status</span>
                  <span className={`font-semibold ${overview.last_quote.current ? 'text-emerald-600' : 'text-amber-600'}`}>
                    {overview.last_quote.current ? 'Price verified' : 'Recalculation needed'}
                  </span>
                </div>
              </div>
              <div className="mt-4 flex justify-end">
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => {
                    if (overview.last_quote.trip_id) {
                      sessionStorage.setItem('mira-workspace-trip', overview.last_quote.trip_id);
                      localStorage.setItem('mira-workspace-trip', overview.last_quote.trip_id);
                    }
                    navigate('/mira');
                  }}
                >
                  Resume in Workspace
                </Button>
              </div>
            </Card>
          )}

          {/* Saved Journeys */}
          <Card className="p-6">
            <h3 className="font-semibold text-sm mb-4">Saved Journeys</h3>
            {overview?.trips?.length > 0 ? (
              <div className="space-y-2.5">
                {overview.trips.map((trip) => (
                  <div key={trip.id} className="flex items-center justify-between gap-3 p-3 rounded-card bg-gray-50 border border-border text-xs">
                    <div className="min-w-0">
                      <p className="font-semibold text-brand-black truncate">{trip.tour_name || trip.tour || 'Sri Lanka Journey'}</p>
                      <p className="text-text-muted mt-0.5">
                        {trip.date || 'Flexible date'} • {trip.adults || 1} adult{(trip.adults || 1) === 1 ? '' : 's'}
                        {trip.updated ? ` • Updated ${new Date(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(String(trip.updated)) ? String(trip.updated).replace(' ', 'T') + 'Z' : trip.updated).toLocaleDateString()}` : ''}
                      </p>
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        sessionStorage.setItem('mira-workspace-trip', trip.id);
                        localStorage.setItem('mira-workspace-trip', trip.id);
                        navigate('/mira');
                      }}
                    >
                      Resume
                    </Button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-text-muted">No saved journeys yet.</p>
            )}
          </Card>

          {/* Recent Quotations */}
          {overview?.quotes?.length > 0 && (
            <Card className="p-6">
              <h3 className="font-semibold text-sm mb-4">Recent Quotations</h3>
              <div className="space-y-2.5">
                {overview.quotes.map((q) => (
                  <div key={q.id} className="flex items-center justify-between gap-3 p-3 rounded-card bg-gray-50 border border-border text-xs">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-mono font-bold text-brand-black">
                          {q.enquiry_reference || `Quote #${String(q.id || '').slice(0, 8).toUpperCase()}`}
                        </span>
                        <span className="font-medium text-text-primary truncate">{q.title}</span>
                        {q.mock_booking_reference && (
                          <span className="px-2 py-0.5 rounded-pill bg-brand-leaf/10 text-brand-leaf font-mono text-[11px]">
                            Demo booking: #{String(q.mock_booking_reference).slice(0, 8).toUpperCase()}
                          </span>
                        )}
                      </div>
                      <p className="text-text-muted mt-0.5">
                        {q.date || 'Flexible'} • USD {q.total} • {q.current ? 'Price verified' : 'Recalculation needed'}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      {q.enquiry_reference && (
                        <Button variant="ghost" size="sm" onClick={() => navigate('/enquiry/' + q.enquiry_reference)}>
                          View Enquiry
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          if (q.trip_id) {
                            sessionStorage.setItem('mira-workspace-trip', q.trip_id);
                            localStorage.setItem('mira-workspace-trip', q.trip_id);
                          }
                          navigate('/mira');
                        }}
                      >
                        Open
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Enquiries List */}
          <Card className="p-6">
            <h3 className="font-semibold text-sm mb-4">Your Enquiries</h3>
            {overview?.enquiries?.length > 0 ? (
              <div className="space-y-3">
                {overview.enquiries.map((enq) => (
                  <div key={enq.id} className="flex items-center justify-between gap-3 p-3 rounded-card bg-gray-50 border border-border text-xs">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-mono font-bold text-brand-black">{enq.reference || enq.id}</span>
                        {enq.tour_name && <span className="font-semibold text-brand-black">{enq.tour_name}</span>}
                        {enq.mock_booking_status && (
                          <span className="px-2 py-0.5 rounded-pill bg-brand-teal/10 text-brand-teal font-medium">
                            Demo booking: {enq.mock_booking_status === 'confirmed' ? 'Confirmed' : enq.mock_booking_status}
                          </span>
                        )}
                      </div>
                      <p className="text-text-muted mt-0.5">{enq.human_reason || enq.reason || 'Trip planning enquiry'}</p>
                      <p className="text-[11px] text-text-muted mt-0.5">
                        {enq.travel_date ? `Date: ${enq.travel_date} • ` : ''}
                        {enq.created ? `Created ${new Date(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(String(enq.created)) ? String(enq.created).replace(' ', 'T') + 'Z' : enq.created).toLocaleString()}` : ''}
                      </p>
                    </div>
                    <div className="flex items-center gap-3 shrink-0">
                      <span className="px-2 py-0.5 rounded-pill font-medium bg-brand-leaf/10 text-brand-leaf capitalize">
                        {enq.status}
                      </span>
                      <Button variant="ghost" size="sm" onClick={() => navigate('/enquiry/' + (enq.reference || enq.id))}>
                        View Status
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-8 text-text-muted text-xs">
                <p>No enquiries submitted yet.</p>
                <button
                  onClick={() => navigate('/mira')}
                  className="mt-2 text-brand-orange font-semibold hover:underline cursor-pointer"
                >
                  Start planning with Mira →
                </button>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* Tab: Edit Profile */}
      {activeTab === 'edit' && (
        <Card className="p-6 max-w-xl">
          <h3 className="font-semibold text-sm mb-4">Edit Personal Information</h3>
          {profileMsg.text && (
            <div className={`mb-4 p-3 rounded-input text-xs ${profileMsg.type === 'success' ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' : 'bg-red-50 text-red-800 border border-red-200'}`}>
              {profileMsg.text}
            </div>
          )}
          <form onSubmit={handleProfileSave} className="space-y-4">
            <div>
              <label className="text-xs font-medium block mb-1">Full Name</label>
              <input
                type="text"
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full px-3 py-2 border border-border rounded-input text-sm"
              />
            </div>
            <div>
              <label className="text-xs font-medium block mb-1">Phone Number</label>
              <input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+94 77 123 4567"
                className="w-full px-3 py-2 border border-border rounded-input text-sm"
              />
            </div>
            <div>
              <label className="text-xs font-medium block mb-1">Dietary Preferences</label>
              <select
                value={dietary}
                onChange={(e) => setDietary(e.target.value)}
                className="w-full px-3 py-2 border border-border rounded-input text-sm bg-white"
              >
                <option value="none">Standard / No restrictions</option>
                <option value="vegetarian">Vegetarian</option>
                <option value="vegan">Vegan</option>
                <option value="halal">Halal</option>
                <option value="gluten-free">Gluten-free</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-medium block mb-1">Preferred Travel Pace</label>
              <select
                value={pace}
                onChange={(e) => setPace(e.target.value)}
                className="w-full px-3 py-2 border border-border rounded-input text-sm bg-white"
              >
                <option value="relaxed">Relaxed (slower pace, more leisure)</option>
                <option value="balanced">Balanced (highlights + downtime)</option>
                <option value="active">Active (packed sights and adventures)</option>
              </select>
            </div>
            <Button variant="primary" disabled={profileBusy}>
              {profileBusy ? 'Saving...' : 'Save Profile Changes'}
            </Button>
          </form>
        </Card>
      )}

      {/* Tab: Password */}
      {activeTab === 'password' && (
        <Card className="p-6 max-w-xl">
          <h3 className="font-semibold text-sm mb-4">Change Account Password</h3>
          {pwdMsg.text && (
            <div className={`mb-4 p-3 rounded-input text-xs ${pwdMsg.type === 'success' ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' : 'bg-red-50 text-red-800 border border-red-200'}`}>
              {pwdMsg.text}
            </div>
          )}
          <form onSubmit={handlePasswordChange} className="space-y-4">
            <div>
              <label className="text-xs font-medium block mb-1">Current Password</label>
              <input
                type="password"
                required
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                className="w-full px-3 py-2 border border-border rounded-input text-sm"
              />
            </div>
            <div>
              <label className="text-xs font-medium block mb-1">New Password (min 8 chars)</label>
              <input
                type="password"
                required
                minLength={8}
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="w-full px-3 py-2 border border-border rounded-input text-sm"
              />
            </div>
            <div>
              <label className="text-xs font-medium block mb-1">Confirm New Password</label>
              <input
                type="password"
                required
                value={confirmNewPassword}
                onChange={(e) => setConfirmNewPassword(e.target.value)}
                className="w-full px-3 py-2 border border-border rounded-input text-sm"
              />
            </div>
            <Button variant="primary" disabled={pwdBusy}>
              {pwdBusy ? 'Updating Password...' : 'Update Password'}
            </Button>
          </form>
        </Card>
      )}
    </div>
  );
}

// ============ STAFF PAGE ============
function StaffPage({ navigate }) {
  const { refreshUser } = useAuth();
  return <StaffConsole defaultTab="overview" onAuthChange={refreshUser} />;
}

// ============ MAIN APP ============
function App() {
  const { route, navigate } = useRouter();
  const [tours, setTours] = useState(INITIAL_TOURS);
  const [destinations, setDestinations] = useState(INITIAL_DESTINATIONS);
  const [guideError, setGuideError] = useState(false);
  const [guideAttempt, setGuideAttempt] = useState(0);

  // Load published guide from backend
  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const res = await fetch('/api/guide');
        if (!res.ok) throw new Error("Guide 503");
        const data = await res.json();
        if (mounted && data) {
          if (data.tours?.length) {
            const mappedTours = data.tours.map((t, idx) => {
              const matched = INITIAL_TOURS.find(it => it.id === t.id);
              return {
                id: t.id,
                slug: matched?.slug || t.slug || (t.id || '').toLowerCase(),
                title: t.title,
                category: t.category || matched?.category || 'Round trip',
                duration: t.duration || matched?.duration || 'Flexible',
                start: t.start || matched?.start || 'Colombo',
                destinations: (t.places && t.places.length > 0) ? t.places : (matched?.destinations || []),
                description: t.summary || t.description || matched?.description || '',
                accent: matched?.accent || (idx % 2 === 0 ? 'brand-orange' : 'brand-teal'),
                imgClass: `tour-img-${(t.id || '').toLowerCase()} tour-img-${(idx % 6) + 1}`,
                itinerary: (t.days && t.days.length > 0)
                  ? t.days.map(d => ({ day: d.number, title: d.title, description: d.body }))
                  : (matched?.itinerary || []),
                inclusions: {
                  included: data.details?.[t.id]?.included || matched?.inclusions?.included || ['Transport', 'Guide'],
                  optional: matched?.inclusions?.optional || [],
                  not_included: data.details?.[t.id]?.excluded || matched?.inclusions?.not_included || [],
                },
              };
            });
            setTours(mappedTours);
            gTours = mappedTours;
          }
          if (data.places && Object.keys(data.places).length > 0) {
            const mappedDestinations = Object.entries(data.places).map(([slug, p]) => {
              const matched = INITIAL_DESTINATIONS.find(d => d.slug === slug);
              return {
                id: p.id,
                slug,
                title: p.name,
                description: p.description || matched?.description || '',
                imgClass: `destination-img-${slug}`,
                accent: matched?.accent || 'brand-teal',
              };
            });
            setDestinations(mappedDestinations);
            gDestinations = mappedDestinations;
          } else if (data.destinations?.length) {
            setDestinations(prev => [...prev, ...data.destinations.filter(d => !prev.some(p => p.slug === d.slug))]);
          }
          setGuideError(false);
        }
      } catch {
        if (mounted) setGuideError(true);
      }
    })();
    return () => { mounted = false; };
  }, [guideAttempt]);

  const renderPage = () => {
    if (route === '/' || route === '') return <HomePage navigate={navigate} />;
    if (route === '/explore') return <ExplorePage navigate={navigate} />;
    if (route === '/tours') return <ToursPage navigate={navigate} />;
    if (route.startsWith('/tours/')) return <TourDetailPage key={route} navigate={navigate} slug={route.replace('/tours/', '')} />;
    if (route === '/destinations') return <DestinationsPage navigate={navigate} />;
    if (route.startsWith('/destinations/')) return <DestinationDetailPage navigate={navigate} slug={route.replace('/destinations/', '')} />;
    if (route === '/mira' || route === '/plan') return <MiraWorkspace navigate={navigate} />;
    if (route === '/about') return <AboutPage />;
    if (route === '/policies') return <PoliciesPage navigate={navigate} />;
    if (route.startsWith('/policies/')) return <PolicyDetailPage navigate={navigate} slug={route.replace('/policies/', '')} />;
    if (route.startsWith('/enquiry/')) return <EnquiryPage navigate={navigate} reference={route.replace('/enquiry/', '').split('?')[0]} tours={tours} />;
    if (route === '/login' || route === '/sign-in') return <LoginPage navigate={navigate} />;
    if (route === '/register') return <RegisterPage navigate={navigate} />;
    if (route === '/profile') return <ProfilePage navigate={navigate} />;
    if (route === '/staff' || route.startsWith('/staff')) return <StaffPage navigate={navigate} />;
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24 text-center">
        <h1 className="text-xl font-bold mb-4">Page not found</h1>
        <Button onClick={() => navigate('/')}>Go home</Button>
      </div>
    );
  };

  const showFooter = !route.startsWith('/mira') && !route.startsWith('/plan') && !route.startsWith('/staff') && route !== '/login' && route !== '/sign-in' && route !== '/register';

  return (
    <AuthProvider>
      <AppContext.Provider value={{ 
        tours, 
        destinations, 
        guideError, 
        retryGuide: () => setGuideAttempt(n => n + 1) 
      }}>
        <div className="min-h-screen flex flex-col">
          {guideError && (
            <div className="bg-amber-50 border-b border-amber-200 px-4 py-2 text-xs text-amber-800 flex items-center justify-between" role="alert">
              <span>Guide content is temporarily unavailable. Displaying local catalogue.</span>
              <button 
                onClick={() => setGuideAttempt(n => n + 1)} 
                className="font-bold underline cursor-pointer ml-3"
              >
                Retry
              </button>
            </div>
          )}
          <Navbar navigate={navigate} route={route} />
          <main className="flex-1">
            {renderPage()}
          </main>
          {showFooter && <Footer navigate={navigate} />}
        </div>
      </AppContext.Provider>
    </AuthProvider>
  );
}

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }
  componentDidCatch(error, errorInfo) {
    console.error("Workspace preview error:", error, errorInfo);
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="p-8 max-w-xl mx-auto my-12 bg-red-50 border border-red-200 rounded-xl text-red-900 font-sans">
          <h2 className="text-lg font-bold mb-2">Display Error in Workspace</h2>
          <p className="text-sm mb-4">An error occurred while rendering the page components:</p>
          <pre className="text-xs bg-white p-4 rounded border border-red-100 overflow-x-auto">{String(this.state.error?.stack || this.state.error)}</pre>
        </div>
      );
    }
    return this.props.children;
  }
}

const rootEl = document.getElementById("root");
if (rootEl) {
  createRoot(rootEl).render(
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  );
}

export { App, MiraWorkspace, UIComponentRenderer, HomePage, TourDetailPage, EnquiryPage, ProfilePage, AuthProvider };
