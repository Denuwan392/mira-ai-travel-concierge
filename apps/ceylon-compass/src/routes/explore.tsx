import { createFileRoute } from "@tanstack/react-router";
import { EditorialSlideshow } from "@/components/site/EditorialSlideshow";
import { Footer } from "@/components/site/Footer";
export const Route = createFileRoute("/explore")({ component: Page });
function Page() {
  return (
    <>
      <main className="pt-[72px]">
        <EditorialSlideshow />
      </main>
      <Footer />
    </>
  );
}
