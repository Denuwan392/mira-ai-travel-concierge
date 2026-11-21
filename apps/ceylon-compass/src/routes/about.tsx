import { createFileRoute } from "@tanstack/react-router";
import { WhySection } from "@/components/site/WhySection";
import { Footer } from "@/components/site/Footer";
export const Route = createFileRoute("/about")({ component: Page });
function Page() {
  return (
    <>
      <main className="pt-[72px]">
        <WhySection />
      </main>
      <Footer />
    </>
  );
}
