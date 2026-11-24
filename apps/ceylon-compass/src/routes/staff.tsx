import { createFileRoute, Link } from "@tanstack/react-router";
import { StaffConsole } from "@/components/staff/StaffConsole";

export const Route = createFileRoute("/staff")({
  component: StaffDashboardPage,
});

export default function StaffDashboardPage() {
  return (
    <main className="min-h-screen bg-[#faf9f6] pb-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-4 flex items-center justify-between text-xs text-[#5F5F5F]">
        <Link to="/" className="hover:text-[#111111] font-medium">
          ← Back to Ceylon Compass Home
        </Link>
        <a href="/workspace/index.html#/mira" className="hover:text-[#111111] font-medium">
          Open Travel Workspace →
        </a>
      </div>
      <StaffConsole defaultTab="overview" />
    </main>
  );
}
