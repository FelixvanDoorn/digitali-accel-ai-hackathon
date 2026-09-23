import { createFileRoute } from "@tanstack/react-router";
import { ArrowRight, BookOpen, ClipboardList, FileText, Menu, MessageCircle, ReceiptText, X } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { BrandLockup, DropRow } from "@/components/wordmark";
import { PhotoDemo } from "@/components/photo-demo";
import { WhatsAppDemo } from "@/components/whatsapp-demo";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Digitali — Less admin. More impact." },
      { name: "description", content: "Digitali reads the forms, notes and receipts field teams already produce and turns them into one clean database, so staff lose fewer hours to admin and managers decide with data." },
      { property: "og:title", content: "Digitali — Less admin. More impact." },
      { property: "og:description", content: "Data-driven decisions for organisations in the field. Any input in — paper, photos, scans, messages — one clean database out." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: Index,
});

const steps = [
  ["01 · Piga picha", "Take a photo", "Use the paper you already have. Handwriting and phone photos are welcome."],
  ["02 · Tuma", "Send it", "WhatsApp is how it will arrive. Today you can upload the photo on this page."],
  ["03 · Pata orodha", "Get a clean list back", "Check each line, correct anything unclear, then keep or share it."],
];

const recordTypes = [
  [ClipboardList, "Forms and notes", "Attendance sheets, meeting minutes, visit reports."],
  [FileText, "Scans and PDFs", "Old registers, agreements, reports already filed."],
  [ReceiptText, "Receipts", "Dates, items and amounts."],
  [BookOpen, "Messages", "Photos and notes already sitting in a WhatsApp group."],
] as const;

const pills = ["All sorts of inputs", "One clean database", "API or our web tool", "Dashboards and decisions"];

function KangaSaying({ children, translation }: { children: string; translation: string }) {
  return <div className="kanga"><DropRow /><div>{children}</div><DropRow /><p>{translation}</p></div>;
}

const IMG = {
  portrait: "/images/asha-portrait.jpg",
  group: "/images/group-circle.jpg",
  meeting: "/images/savings-ledger.jpg",
  night: "https://images.unsplash.com/photo-1566699270403-3f7e3f340664",
  register: "https://images.unsplash.com/photo-1526656001029-20a71b17f7ba",
};

function ArchPhoto({ src, alt, caption, compact = false, position = "center" }: { src: string; alt: string; caption?: string; compact?: boolean; position?: string }) {
  const url = src.startsWith("http") ? `${src}?w=1200&q=80&auto=format&fit=crop` : src;
  return (
    <figure className={compact ? "arch-photo compact" : "arch-photo"}>
      <div className="arch-img" role="img" aria-label={alt} style={{ backgroundImage: `url('${url}')`, backgroundPosition: position }} />
      {caption && <figcaption>{caption}</figcaption>}
    </figure>
  );
}

function ArchPlaceholder({ caption, compact = false }: { caption: string; compact?: boolean }) {
  return <div className={compact ? "arch-placeholder compact" : "arch-placeholder"}><img src="/brand/digitali-mark.svg" alt="" /><p>{caption}</p></div>;
}

function Index() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [replay, setReplay] = useState(0);

  function showWhatsAppDemo() {
    setReplay((current) => current + 1);
    document.getElementById("whatsapp")?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  return (
    <main>
      <nav className="site-nav" aria-label="Main navigation">
        <a href="#top" aria-label="Digitali home"><BrandLockup /></a>
        <div className={menuOpen ? "nav-links open" : "nav-links"}>
          <a href="#how" onClick={() => setMenuOpen(false)}>How it works</a>
          <a href="#who" onClick={() => setMenuOpen(false)}>Who it's for</a>
          <a href="#pricing" onClick={() => setMenuOpen(false)}>Pricing</a>
          <span className="language" aria-label="Language"><b>EN</b><i />SW</span>
        </div>
        <Button className="menu-button" variant="ghost" size="icon" aria-label={menuOpen ? "Close menu" : "Open menu"} onClick={() => setMenuOpen(!menuOpen)}>{menuOpen ? <X /> : <Menu />}</Button>
      </nav>

      <section id="top" className="hero page-wrap">
        <div className="hero-copy">
          <p className="eyebrow">Karibu · Welcome</p>
          <h1>Less admin. More impact.</h1>
          <p className="lead">Data-driven decisions for organisations in the field. Digitali reads the forms, notes and receipts your staff already produce, and turns them into one clean database you can check, query and keep.</p>
          <div className="hero-actions">
            <Button size="lg" onClick={showWhatsAppDemo}><MessageCircle aria-hidden="true" /> See the demo on WhatsApp</Button>
            <Button asChild size="lg" variant="outline"><a href="/pitch-deck/index.html">Pitch deck <ArrowRight aria-hidden="true" /></a></Button>
          </div>
          <p className="caption">Works in Swahili, English and French. Handwriting welcome.</p>
        </div>
        <ArchPhoto src={IMG.group} alt="A women's group meeting together" position="center 30%" />
      </section>

      <div className="page-wrap"><KangaSaying translation="Little by little fills the measure.">Haba na haba hujaza kibaba</KangaSaying></div>

      <section id="user" className="user section page-wrap">
        <ArchPhoto src={IMG.portrait} alt="Asha, a field officer in western Kenya" position="center 35%" />
        <div>
          <p className="eyebrow">The user</p>
          <h2>Meet Asha.</h2>
          <p className="lead">Field officer in western Kenya. She supports twelve community groups, and every meeting ends on paper.</p>
        </div>
      </section>

      <section className="field-strip page-wrap" aria-label="A day in the field">
        {([
          ["/images/field-walk.jpg", "Walking between villages"],
          ["/images/home-visit.jpg", "Home visits"],
          ["/images/water-point.jpg", "Project check-ins"],
          ["/images/photo-sheet.jpg", "One photo of the sheet"],
        ] as const).map(([src, caption]) => (
          <ArchPhoto key={src} compact src={src} alt={caption} caption={caption} />
        ))}
      </section>

      <section id="whatsapp" className="whatsapp section page-wrap">
        <div className="section-heading"><div><p className="eyebrow">On WhatsApp</p><h2>Send the photo the way you already do.</h2></div><p>A preview of the WhatsApp flow, shown here on the page. The names and numbers are made up for testing.</p></div>
        <WhatsAppDemo replay={replay} />
      </section>

      <section className="problem section page-wrap">
        <p className="eyebrow">The problem</p>
        <h2>Field organisations exist to help people. Too much of their time goes to admin.</h2>
        <div className="story-strip">
          <ArchPhoto compact src={IMG.meeting} alt="Women at an outdoor community group meeting" position="center 40%" caption="Every meeting ends on paper." />
          <ArrowRight aria-hidden="true" />
          <ArchPhoto compact src={IMG.night} alt="A branch office desk buried in paper" position="center 40%" caption="Back at the branch, hours go to retyping." />
          <ArrowRight aria-hidden="true" />
          <ArchPhoto compact src={IMG.register} alt="Binders full of paper files" caption="The organisation has no data to decide or report." />
        </div>
      </section>

      <section id="how" className="section page-wrap">
        <p className="eyebrow">How it works</p><h2>Three steps. No new habits.</h2>
        <div className="steps">{steps.map(([number, title, text]) => <article key={number}><span>{number}</span><h3>{title}</h3><p>{text}</p></article>)}</div>
      </section>

      <section className="reads section page-wrap">
        <p className="eyebrow">The product</p><h2>A data collection system that accepts anything staff already produce.</h2>
        <div className="record-grid">{recordTypes.map(([Icon, title, text]) => <article key={title}><Icon strokeWidth={1.3} aria-hidden="true" /><h3>{title}</h3><p>{text}</p></article>)}</div>
        <div className="pills">{pills.map((pill) => <span key={pill}>{pill}</span>)}</div>
        <p className="caption">Open models do the reading, against your own form and field names. The point is the database: every input lands as a clean record you can query, report on and decide with.</p>
      </section>

      <section id="demo" className="section page-wrap">
        <div className="section-heading"><div><p className="eyebrow">Try it here</p><h2>One photo in. A clean list out.</h2></div><p>Try a real attendance sheet. Your photo is read once and never stored.</p></div>
        <PhotoDemo />
      </section>

      <section id="who" className="who section page-wrap">
        <div><p className="eyebrow">Who it's for</p><h2>Less admin for the field officer. Better decisions for the manager.</h2></div>
        <ul>{["Cooperatives and chamas", "SACCOs", "Microfinance", "School and clinic offices", "Church and mosque committees", "NGOs and field teams", "Small shops"].map((item) => <li key={item}>{item}</li>)}</ul>
        <KangaSaying translation="Unity is strength.">Umoja ni nguvu</KangaSaying>
      </section>

      <section className="trust section page-wrap">
        <p className="eyebrow">Made with care</p><h2>Your records stay yours.</h2>
        <div>{["Your photos are never stored.", "You check everything before it's saved.", "Built on open models, so your data can stay close to home."].map((item) => <p key={item}>{item}</p>)}</div>
      </section>

      <section id="pricing" className="pricing section page-wrap">
        <p className="eyebrow">Pricing</p><h2>Start small. Grow when you need to.</h2>
        <div className="price-grid"><article><h3>Free for small groups</h3><p>Try Digitali with the records you already have.</p><a className="text-link" href="#demo">Send your first photo <ArrowRight /></a></article><article><h3>For organisations</h3><p><strong>[PRICE]</strong> per month</p><p>For teams with more pages and their own record format.</p><a className="text-link" href="mailto:hello@digitali.africa">Talk to us <ArrowRight /></a></article></div>
      </section>

      <section className="pitch section page-wrap">
        <p className="eyebrow">The pitch</p><h2>Why Digitali, and why now.</h2>
        <div className="pitch-track">{[
          ["01", "The problem", "Field organisations exist to help people. Too much of their time goes to admin."],
          ["02", "The user", "Less admin for the field officer. Better decisions for the manager."],
          ["03", "The product", "Any input staff already produce: forms, handwritten notes, receipts, scans, PDFs and messages."],
          ["04", "The engine", "Open models on Nebius read the page and map it to the organisation's own data model."],
          ["05", "The output", "A database. Reach it through our API, or use our web tool if there is no IT capacity."],
          ["06", "The company", "Every field organisation is a customer. Every hour saved goes back to impact."],
        ].map(([n, title, text]) => <article key={n}><span>{n}</span><h3>{title}</h3><p>{text}</p></article>)}</div>
        <p className="pitch-note">The full deck is one click away: <a className="text-link" href="/pitch-deck/index.html">open the pitch deck <ArrowRight /></a></p>
      </section>

      <footer><div className="footer-inner"><div className="footer-brand"><BrandLockup inverse /><p>Kutoka karatasi hadi data<br/><span>From paper to data</span></p></div><div className="footer-links"><a href="#how">How it works</a><a href="#who">Who it's for</a><a href="#pricing">Pricing</a><a href="/pitch-deck/index.html">Pitch deck</a><a href="#demo">Try it</a></div><p className="asante">Asante.</p><p className="credits">Field scenes are AI generated; office photos from Unsplash (Wonderlane, Sear Greyson). Asha is a persona.</p></div></footer>
    </main>
  );
}
