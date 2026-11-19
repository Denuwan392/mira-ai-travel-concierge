import { destinationMedia } from "../../lib/media-manifest";

export default function Credits(){
  return <main className="credits frame"><h1>Photography</h1><p>Editorial views of Sri Lanka. Each photographer and original image are credited below.</p>
    {Object.entries(destinationMedia).map(([id,p])=><article key={id}><h2>{p.location}</h2><p>{p.author} · {p.license}</p><a href={p.source}>Original photograph</a></article>)}</main>;
}
