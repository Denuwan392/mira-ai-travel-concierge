import { Link } from "@tanstack/react-router";
import { photos } from "@/lib/photos";
import { Eyebrow } from "./SectionHeading";

const chapters = [
  { photo: photos.tea, place: "Hill country", title: "Set your own pace.", body: "Tell Mira how many days you have and where you want to linger. Select a day in your notebook to explore the route.", prompt: "Plan six relaxed days in the hill country with time in Ella" },
  { photo: photos.curry, place: "At the table", title: "Make room for the details.", body: "Build a trip around the things you remember long after you get home. Start with a market morning or an evening around a Sri Lankan table.", prompt: "Plan a cultural trip with local food around Kandy" },
];

export function WhySection() {
  return (
    <section data-nav-theme="light" className="island-notes">
      <div className="notes-intro">
        <Eyebrow>Why Ceylon Compass</Eyebrow>
        <h2>There’s more than one way <em>into the island.</em></h2>
      </div>
      <div className="notes-spread">
        {chapters.map(({ photo, place, title, body, prompt }) => (
          <article key={place}>
            <img src={photo.src} alt={photo.alt} loading="lazy" />
            <div><p className="eyebrow">{place}</p><h3>{title}</h3><p>{body}</p>
              <Link to="/plan" search={{ q: prompt }}>Plan with Mira <span aria-hidden>↗</span></Link>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
