import { createFileRoute, Link } from "@tanstack/react-router";
import { usePublished } from "@/lib/live/published";
import { photos } from "@/lib/photos";
import { Footer } from "@/components/site/Footer";
export const Route = createFileRoute("/experiences")({ component: Experiences });
function Experiences() {
  const { items, status } = usePublished();
  return (
    <>
      <main className="folio">
        <p className="eyebrow">Across the island</p>
        <h1>Experiences</h1>
        <div className="timeline">
          <p role="status">{status}</p>
          {items.map((t) => (
            <article key={t.id}>
              <img src={photos[t.photo].src} alt={photos[t.photo].alt} />
              <div>
                <small>
                  {t.category} · {t.duration} · {t.source}
                </small>
                <h4>{t.title}</h4>
                <p>{t.summary}</p>
                <Link className="pill" to="/plan" search={{ q: "@tour " + t.id }}>
                  Explore itinerary →
                </Link>
              </div>
            </article>
          ))}
        </div>
      </main>
      <Footer />
    </>
  );
}
