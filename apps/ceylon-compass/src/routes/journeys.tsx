import { createFileRoute } from "@tanstack/react-router";
import { FeaturedJourneys } from "@/components/site/FeaturedJourneys";
import { Footer } from "@/components/site/Footer";
export const Route = createFileRoute("/journeys")({ component: Page });
function Page() {
  return (
    <>
      <main className="pt-[72px]">
        <div className="folio !pb-0">
          <h1>Published journeys</h1>
        </div>
        <FeaturedJourneys showHeading={false} />
      </main>
      <Footer />
    </>
  );
}
