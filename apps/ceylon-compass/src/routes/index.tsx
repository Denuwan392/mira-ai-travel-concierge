import { createFileRoute, Link } from "@tanstack/react-router";
import { Hero } from "@/components/site/Hero";
import { DestinationStrip } from "@/components/site/DestinationStrip";
import { WhySection } from "@/components/site/WhySection";
import { EditorialSlideshow } from "@/components/site/EditorialSlideshow";
import { FeaturedJourneys } from "@/components/site/FeaturedJourneys";
import { PromptBar } from "@/components/site/PromptBar";
import { Footer } from "@/components/site/Footer";
import { DEMO_BRIEF } from "@/lib/content";

export const Route = createFileRoute("/")({ component: Home });
function Home() {
  return (
    <>
      <main>
        <Hero />
        <DestinationStrip />
        <WhySection />
        <EditorialSlideshow />
        <FeaturedJourneys />
        <section data-nav-theme="dark" className="spread night">
          <div>
            <p className="eyebrow">Made for you</p>
            <h2>
              Not another tour.
              <br />
              <em>Your tour.</em>
            </h2>
            <p>
              Take the slow train. Stay another night. Mira redraws the route around the things you
              travel for.
            </p>
          </div>
          <Link to="/plan" search={{ q: DEMO_BRIEF }} className="route-ticket">
            <small>✦ MIRA’S FIELD NOTES</small>
            <h3>Hill country to the sea</h3>
            <p>Kandy ━ Ella ━ Mirissa</p>
            <hr />
            <span>6 days · Nature, trains and beaches</span>
            <strong>Shape this journey →</strong>
          </Link>
        </section>
        <section className="spread">
          <div>
            <p className="eyebrow">How Mira works</p>
            <h2>
              From a thought
              <br />
              <em>to a journey.</em>
            </h2>
          </div>
          <ol className="steps">
            {[
              "Describe your trip",
              "Discover your route",
              "Personalise each stop",
              "Review your quote",
              "Prepare your enquiry",
            ].map((s, i) => (
              <li key={s}>
                <small>0{i + 1}</small>
                {s}
              </li>
            ))}
          </ol>
        </section>
        <aside className="trust-note">
          <strong>Clarity before you book.</strong> Your itinerary stays editable. Where a rate
          needs confirmation, Mira prepares an enquiry.
        </aside>
        <section data-nav-theme="dark" className="spread night">
          <div>
            <h2>
              Sri Lanka <em>is waiting.</em>
            </h2>
            <p>Tell Mira how you want to experience it.</p>
          </div>
          <PromptBar id="closing-brief" tone="dark" showStarters={false} />
        </section>
      </main>
      <Footer />
    </>
  );
}
