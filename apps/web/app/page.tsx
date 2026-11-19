"use client";

import Image from "next/image";
import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { queuePrompt } from "../lib/handoff";
import type { Tour } from "../lib/catalog";
import { destinationMedia } from "../lib/media-manifest";
import { CinematicHero } from "./editorial/hero";
import { DestinationPhotoDeck } from "./editorial/deck";

export default function Home(){
  const router=useRouter();
  const [tours,setTours]=useState<Tour[]>();
  const [story,setStory]=useState<{title:string;body:string}>();
  useEffect(()=>{
    api<Tour[]>("/tours").then(setTours).catch(()=>setTours([]));
    api<{title:string;body:string}>("/sources/D05").then(setStory).catch(()=>{});
  },[]);
  function plan(s:string){if(s.trim()){queuePrompt(s.trim());router.push("/plan")}}
  const excerpt=story?.body.split("\n").find(line=>line.trim() && !line.startsWith("#"));
  return <main className="editorial-home">
    <CinematicHero plan={plan}/><DestinationPhotoDeck tours={tours} plan={plan}/>
    {story && excerpt && <section className="field-note frame">
      <div className="story-photo"><Image src={destinationMedia.ella.src} alt={destinationMedia.ella.alt} fill sizes="(max-width: 700px) 90vw, 48vw"/></div>
      <div><span className="overline dark-label">Destination notes</span><h2>{story.title}</h2><p>{excerpt}</p><details><summary>Read the published source · D05</summary><p>{story.body.replace(/^#+ /gm,"").replaceAll("**","")}</p></details></div>
    </section>}
    <section id="how" className="mira-guide frame"><div><span className="overline dark-label">Meet Mira</span><h2>From conversation<br/>to journey.</h2></div>
      <ol><li><strong>Tell Mira your plans</strong><p>Start with a place, a date or the people coming with you.</p></li><li><strong>Explore published tours</strong><p>Read the itinerary and open its source as you go.</p></li><li><strong>Check your travel details</strong><p>Get a verified quote or save an enquiry for a specialist.</p></li></ol>
    </section>
    <section className="closing"><Image src={destinationMedia.coast.src} alt={destinationMedia.coast.alt} fill sizes="100vw"/><div><h2>Where to next?</h2><Link href="/plan" className="lux-action">Start planning with Mira <ArrowUpRight size={18}/></Link></div></section>
  </main>
}
