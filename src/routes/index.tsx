import { createFileRoute } from "@tanstack/react-router";
import { ArrowRight, BookOpen, ClipboardList, FileText, Menu, ReceiptText, X } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { BrandLockup, DropRow, Wordmark } from "@/components/wordmark";
import { PhotoDemo } from "@/components/photo-demo";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Digitali — From paper to data, one photo at a time" },
      { name: "description", content: "Turn attendance sheets, meeting notes, receipts and ledgers into clean digital lists with one photo." },
      { property: "og:title", content: "Digitali — From paper to data" },
      { property: "og:description", content: "Send a photo of a paper record. Get back a clean list you can check, share and keep." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary" },
    ],
  }),
  component: Index,
});

const steps = [
  ["01 · Piga picha", "Take a photo", "Use the paper you already have. Handwriting and phone photos are welcome."],
  ["02 · Tuma", "Send it", "Upload it here today. WhatsApp delivery is the next step."],
  ["03 · Pata orodha", "Get a clean list back", "Check each line, correct anything unclear, then keep or share it."],
];

const recordTypes = [
  [ClipboardList, "Attendance sheets", "Names, contacts and signatures."],
  [BookOpen, "Meeting minutes", "Decisions, actions and owners."],
  [ReceiptText, "Receipts", "Dates, items and amounts."],
  [FileText, "Ledgers", "Entries, balances and notes."],
] as const;

function KangaSaying({ children, translation }: { children: string; translation: string }) {
  return <div className="kanga"><DropRow /><div>{children}</div><DropRow /><p>{translation}</p></div>;
}

function ArchPlaceholder({ caption, compact = false }: { caption: string; compact?: boolean }) {
  return <div className={compact ? "arch-placeholder compact" : "arch-placeholder"}><img src="/brand/digitali-mark.svg" alt="" /><p>{caption}</p></div>;
}

function Index() {
  const [menuOpen, setMenuOpen] = useState(false);
  return (
    <main>
      <nav className="site-nav" aria-label="Main navigation">
        <a href="#top" aria-label="Digitali home"><BrandLockup /></a>
        <div className={menuOpen ? "nav-links open" : "nav-links"}>
          <a href="#how" onClick={() => setMenuOpen(false)}>How it works</a>
          <a href="#who" onClick={() => setMenuOpen(false)}>Who it's for</a>
          <a href="#pricing" onClick={() => setMenuOpen(false)}>Pricing</a>
          <a href="/pitch-deck/index.html" onClick={() => setMenuOpen(false)}>Pitch deck</a>
          <span className="language" aria-label="Language"><b>EN</b><i />SW</span>
          <Button asChild><a href="#demo" onClick={() => setMenuOpen(false)}>Try it free</a></Button>
        </div>
        <Button className="menu-button" variant="ghost" size="icon" aria-label={menuOpen ? "Close menu" : "Open menu"} onClick={() => setMenuOpen(!menuOpen)}>{menuOpen ? <X /> : <Menu />}</Button>
      </nav>

      <section id="top" className="hero page-wrap">
        <div className="hero-copy">
          <p className="eyebrow">Karibu · Welcome</p>
          <h1>From paper to data, one photo at a time.</h1>
          <p className="lead">Take a photo of your attendance sheet, meeting notes or receipt. Upload it here. Get back a clean list you can search, share and keep.</p>
          <div className="hero-actions"><Button asChild size="lg"><a href="#demo">Send your first photo</a></Button><Button asChild size="lg" variant="outline"><a href="#how">See how it works</a></Button></div>
          <p className="caption">Works in Swahili, English and French. Handwriting welcome.</p>
        </div>
        <ArchPlaceholder caption="Photo to be made: hands holding a handwritten sign-in sheet in warm daylight." />
      </section>

      <div className="page-wrap"><KangaSaying translation="Little by little fills the measure.">Haba na haba hujaza kibaba</KangaSaying></div>

      <section className="problem section page-wrap">
        <p className="eyebrow">The paper trail</p>
        <h2>Today, the minutes are a photo lost in a WhatsApp group.</h2>
        <div className="story-strip">
          <ArchPlaceholder compact caption="A paper register filled in together." />
          <ArrowRight aria-hidden="true" />
          <ArchPlaceholder compact caption="A quick photo shared in the group." />
          <ArrowRight aria-hidden="true" />
          <ArchPlaceholder compact caption="Useful information, hard to find again." />
        </div>
      </section>

      <section id="how" className="section page-wrap">
        <p className="eyebrow">How it works</p><h2>Three steps. No new habits.</h2>
        <div className="steps">{steps.map(([number, title, text]) => <article key={number}><span>{number}</span><h3>{title}</h3><p>{text}</p></article>)}</div>
      </section>

      <section className="reads section page-wrap">
        <p className="eyebrow">What it reads</p><h2>The records you already use.</h2>
        <div className="record-grid">{recordTypes.map(([Icon, title, text]) => <article key={title}><Icon strokeWidth={1.3} aria-hidden="true" /><h3>{title}</h3><p>{text}</p></article>)}</div>
      </section>

      <section id="demo" className="section page-wrap">
        <div className="section-heading"><div><p className="eyebrow">See it work</p><h2>One photo in. A clean list out.</h2></div><p>Try a real attendance sheet. Your photo is read once and never stored.</p></div>
        <PhotoDemo />
      </section>

      <section id="who" className="who section page-wrap">
        <div><p className="eyebrow">Who it's for</p><h2>Made for the people who keep the records.</h2></div>
        <ul>{["Cooperatives and chamas", "SACCOs", "School and clinic offices", "Church and mosque committees", "NGOs and field teams", "Small shops"].map((item) => <li key={item}>{item}</li>)}</ul>
        <KangaSaying translation="Unity is strength.">Umoja ni nguvu</KangaSaying>
      </section>

      <section className="trust section page-wrap">
        <p className="eyebrow">Made with care</p><h2>Your records stay yours.</h2>
        <div>{["Your photos are never stored.", "You check everything before it's saved.", "Built on open models, so your data can stay close to home."].map((item) => <p key={item}>{item}</p>)}</div>
      </section>

      <section id="pricing" className="pricing section page-wrap">
        <p className="eyebrow">Pricing</p><h2>Start small. Grow when you need to.</h2>
        <div className="price-grid"><article><h3>Free for small groups</h3><p>Try Digitali with the records you already have.</p><Button asChild size="lg"><a href="#demo">Send your first photo</a></Button></article><article><h3>For organisations</h3><p><strong>[PRICE]</strong> per month</p><p>For teams with more pages and their own record format.</p><a className="text-link" href="mailto:hello@digitali.africa">Talk to us <ArrowRight /></a></article></div>
      </section>

      <section className="pitch section page-wrap">
        <p className="eyebrow">The pitch</p><h2>Why Digitali, and why now.</h2>
        <div className="pitch-track">{[
          ["01", "The problem", "Paper works. Retyping it does not. Records arrive late, with errors, or never reach a useful system."],
          ["02", "The insight", "Keep the familiar paper. Change only what happens after someone takes a photo."],
          ["03", "The product", "Image and record format in. A checked, editable list and structured JSON out."],
          ["04", "Built today", "A web upload and one extraction endpoint, powered by an open vision model on Nebius Token Factory."],
          ["05", "Measured honestly", "Test against hand-typed truth: field accuracy, reference matches, cost per page and response time."],
          ["06", "Responsible by design", "Synthetic test data, no stored photos, low-confidence flags and a person confirming every result."],
        ].map(([n, title, text]) => <article key={n}><span>{n}</span><h3>{title}</h3><p>{text}</p></article>)}</div>
        <div className="hero-actions"><Button asChild size="lg" variant="outline"><a href="/pitch-deck/index.html">Open the full pitch deck <ArrowRight /></a></Button></div>
      </section>

      <footer><div className="footer-inner"><div className="footer-brand"><BrandLockup inverse /><p>Kutoka karatasi hadi data<br/><span>From paper to data</span></p></div><div className="footer-links"><a href="#how">How it works</a><a href="#who">Who it's for</a><a href="#pricing">Pricing</a><a href="/pitch-deck/index.html">Pitch deck</a><a href="#demo">Try it</a></div><p className="asante">Asante.</p></div></footer>
    </main>
  );
}
