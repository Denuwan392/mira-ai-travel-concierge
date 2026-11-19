import Image from "next/image";
import { destinationMedia } from "../../lib/media-manifest";

const locations: Record<string,keyof typeof destinationMedia> = {
  T01:"sigiriya",T04:"galle",T05:"mirissa",T06:"tea",T08:"tea",T09:"sigiriya",T10:"ella",T11:"mirissa",T12:"ella",T16:"sigiriya",
};
export function TourPhoto({id,timeline=false}:{id:string;timeline?:boolean}){
  const location=locations[id];
  if(!location)return null;
  const photo=destinationMedia[location];
  return <div className={timeline?"timeline-photo":"journey-photo"}><Image src={photo.src} placeholder="blur" blurDataURL={photo.blurDataURL} alt={`Editorial photograph: ${photo.alt}`} fill sizes={timeline?"(max-width:740px) 96vw, 50vw":"320px"}/></div>;
}
