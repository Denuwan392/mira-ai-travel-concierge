import { createFileRoute } from "@tanstack/react-router";
import { DestinationStrip } from "@/components/site/DestinationStrip";
import { Footer } from "@/components/site/Footer";
export const Route = createFileRoute("/destinations")({ component: Page });
function Page() {
  return (
    <>
      <main className="pt-[72px]">
        <DestinationStrip />
      </main>
      <Footer />
    </>
  );
}
