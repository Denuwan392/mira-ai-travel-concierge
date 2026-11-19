"use client";

import Image from "next/image";
import { ArrowUpRight, ChevronLeft, ChevronRight, MapPin } from "lucide-react";
import { useState } from "react";
import { starters } from "../../lib/api";
import { destinationMedia } from "../../lib/media-manifest";

import { PremiumActionButton } from "./action";

const scenes = ["sigiriya", "ella", "mirissa"] as const;
export function CinematicHero({ plan }: { plan: (prompt:string) => void }) {
  const [scene, setScene] = useState(0);
  const [entry, setEntry] = useState("");
  const key = scenes[scene];
  const photo = destinationMedia[key];
  return <section className="cinema" aria-label="Plan your Sri Lankan journey">
    {key === "sigiriya" ? <picture>
      <source media="(max-width: 640px)" srcSet="/media/destinations/sigiriya-mobile.webp"/>
      <source media="(max-width: 1280px)" srcSet="/media/destinations/sigiriya-medium.webp"/>
      <img className="scene-photo" src="/media/destinations/sigiriya-wide.webp" alt={photo.alt} width={2200} height={1300} fetchPriority="high"/>
    </picture> : <Image className="scene-photo" src={photo.src} alt={photo.alt} placeholder="blur" blurDataURL={photo.blurDataURL} fill sizes="100vw" priority/>}
    <div className="cinema-inner">
      <div className="hero-intro"><span className="overline">Ceylon Compass Holidays</span>
        <h1>Your island.<br/><em>Your story.</em></h1>
        <p>A personal way to explore Sri Lanka.<br/>Tell Mira what moves you.</p>
      </div>
      <form className="travel-entry" onSubmit={e=>{e.preventDefault();plan(entry)}}>
        <label htmlFor="starter"><span className="mira-dot"/> Plan with Mira</label>
        <div><textarea id="starter" rows={1} required maxLength={1200} value={entry} placeholder="Where would you like to go?" onChange={e=>setEntry(e.target.value)} onKeyDown={e=>{if(e.key==="Enter" && !e.shiftKey && !e.nativeEvent.isComposing){e.preventDefault();plan(entry)}}}/>
        <PremiumActionButton variant="primary" className="ask" aria-label="Start planning"><ArrowUpRight size={22}/></PremiumActionButton></div>
      </form>
      <div className="suggestions">{starters.map(s=><button key={s} onClick={()=>plan(s)}>{s}<ArrowUpRight size={12}/></button>)}</div>
    </div>
    <div className="scene-index">
      <div><span className="scene-count">0{scene+1} / 03</span><span className="scene-place"><MapPin size={15}/>{photo.location}</span></div>
      <button aria-label="Previous landscape" onClick={()=>setScene((scene+2)%3)}><ChevronLeft/></button>
      <button aria-label="Next landscape" onClick={()=>setScene((scene+1)%3)}><ChevronRight/></button>
    </div>
  </section>
}
