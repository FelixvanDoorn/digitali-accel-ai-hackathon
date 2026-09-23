import { createFileRoute } from "@tanstack/react-router";
import { BrandLockup } from "@/components/wordmark";
import { Dashboard } from "@/components/dashboard";

export const Route = createFileRoute("/dashboard")({
  head: () => ({
    meta: [
      { title: "Dashboard — Digitali" },
      {
        name: "description",
        content: "Operational insights from everything Digitali has read from paper.",
      },
      { name: "robots", content: "noindex" },
    ],
  }),
  component: DashboardPage,
});

function DashboardPage() {
  return (
    <main>
      <nav className="site-nav" aria-label="Main navigation">
        <a href="/" aria-label="Digitali home">
          <BrandLockup />
        </a>
        <div className="nav-links">
          <a href="/#demo">Try the demo</a>
        </div>
      </nav>
      <Dashboard />
    </main>
  );
}
