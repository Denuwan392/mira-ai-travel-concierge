"use client";

import Image from "next/image";
import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import { ArrowLeft, ArrowRight, ArrowUpRight, Compass } from "lucide-react";
import { destinationMedia } from "../../lib/media-manifest";
import type { Tour } from "../../lib/catalog";

import { PremiumActionButton } from "./action";

const Atlas = dynamic(()=>import("./atlas"), {ssr:false});
const features = [
  {id:"T01",place:"Sigiriya",photo:"sigiriya"},
  {id:"T08",place:"Hill country",photo:"tea"},
  {id:"T05",place:"Mirissa",photo:"mirissa"},
  {id:"T04",place:"Galle Fort",photo:"galle"},
] as const;

export function DestinationPhotoDeck({ tours, plan }: {tours?:Tour[];plan:(s:string)=>void}) {
  const [selected,setSelected] = useState(0);
  const [atlas,setAtlas] = useState(false);
  const [unavailable, setUnavailable] = useState(false);
  const [capable,setCapable] = useState(false);
  useEffect(()=>{
    const query = matchMedia("(min-width: 1000px) and (hover: hover) and (prefers-reduced-motion: no-preference)");
    function sync(){setCapable(query.matches && !document.hidden)}
    sync(); query.addEventListener("change",sync); document.addEventListener("visibilitychange",sync);
    return ()=>{query.removeEventListener("change",sync);document.removeEventListener("visibilitychange",sync)};
  },[]);
  function toggleCompass() {
    if (atlas) { setAtlas(false); return; }
    const probe = document.createElement("canvas").getContext("webgl2");
    if (!probe) { setUnavailable(true); return; }
    probe.getExtension("WEBGL_lose_context")?.loseContext();
    setAtlas(true);
  }
  const choices=features.flatMap(f=>{const tour=tours?.find(t=>t.id===f.id);return tour?[{...f,tour}]:[]});
  const active=choices[selected] ?? choices[0];
  return <section className="collection frame" id="explore">
    <div className="collection-heading"><div><span className="overline dark-label">The journey collection</span><h2>Explore journeys</h2></div>
      {active && <div className="deck-controls"><button aria-label="Previous journey" onClick={()=>setSelected((selected+choices.length-1)%choices.length)}><ArrowLeft/></button><button aria-label="Next journey" onClick={()=>setSelected((selected+1)%choices.length)}><ArrowRight/></button></div>}</div>
    {active ? <>
      <div className="deck-stage">
        <Image src={destinationMedia[active.photo].src} alt={destinationMedia[active.photo].alt} fill sizes="90vw"/>
        <div className="deck-copy"><span className="overline">{active.tour.category} · {active.tour.duration}</span><h3>{active.place}</h3><p>{active.tour.summary}</p>
        <PremiumActionButton variant="light" onClick={()=>plan(`@tour ${active.id}`)}>Plan this journey <ArrowUpRight size={16}/></PremiumActionButton></div>
        {capable && !unavailable && <div className="atlas-box">{atlas && <Atlas selected={selected} count={choices.length} select={setSelected} failed={()=>{setAtlas(false);setUnavailable(true)}}/>}
          <button className="atlas-toggle" aria-pressed={atlas} onClick={toggleCompass}><Compass size={16}/>{atlas?"Close compass":"Explore by compass"}</button></div>}
      </div>
      <div className="contact-sheet">{choices.map((f,i)=><button className="photo-tile" key={f.id} aria-pressed={selected===i} onClick={()=>setSelected(i)}>
        <div className="tile-media"><Image src={destinationMedia[f.photo].src} alt="" fill sizes="(max-width: 640px) 40vw, 20vw"/></div>
        <span className="tile-label">{f.place}</span><h3>{f.tour.title}</h3></button>)}</div>
    </> : <p role="status">{tours ? "No featured journeys are available. Ask Mira about a custom enquiry." : "Loading published journeys…"}</p>}
  </section>
}
