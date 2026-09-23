import { useCallback, useEffect, useRef, useState } from "react";
import { ArrowRight, CheckCheck, RotateCcw } from "lucide-react";
import { Wordmark } from "@/components/wordmark";

type Message =
  | { id: string; from: "me"; kind: "photo" }
  | { id: string; from: "me"; kind: "text"; sw: string; en: string }
  | { id: string; from: "them"; kind: "list"; sw: string; en: string }
  | { id: string; from: "them"; kind: "text"; sw: string; en: string };

const rows = [
  { name: "Amina Hassan", role: "Treasurer", phone: "0712 440 983", unclear: false },
  { name: "Neema Juma", role: "Member", phone: "0754 120 648", unclear: false },
  { name: "Rehema Ali", role: "Member", phone: "0788 39? 211", unclear: true },
  { name: "Fatma Said", role: "Secretary", phone: "0741 602 457", unclear: false },
];

const messages: Message[] = [
  { id: "photo", from: "me", kind: "photo" },
  {
    id: "ask",
    from: "me",
    kind: "text",
    sw: "Attendance ya mkutano wa jana — nipe orodha nzuri.",
    en: "Yesterday's meeting attendance — send me a clean list.",
  },
  {
    id: "list",
    from: "them",
    kind: "list",
    sw: "Karibu. Hii ndiyo orodha yako:",
    en: "Here is your list. Check the highlighted line.",
  },
  {
    id: "fix",
    from: "me",
    kind: "text",
    sw: "Asante — narekebisha namba ya Rehema.",
    en: "Thanks — I'm correcting Rehema's number.",
  },
  {
    id: "saved",
    from: "them",
    kind: "text",
    sw: "Imehifadhiwa: digitali-attendance.json",
    en: "Saved · 4 records · nothing is stored until you confirm.",
  },
];

function Stamp() {
  return (
    <span className="wa-stamp">
      10:24
      <CheckCheck aria-hidden="true" />
    </span>
  );
}

function Bubble({ message }: { message: Message }) {
  const mine = message.from === "me";
  return (
    <div className={mine ? "wa-row me" : "wa-row"}>
      <div className={mine ? "wa-bubble me" : "wa-bubble"}>
        {message.kind === "photo" && (
          <>
            <div className="paper-sheet small" aria-label="Example handwritten attendance sheet">
              <p>Jumuiya ya Tumaini</p>
              <span>Meeting attendance · 14 June</span>
              {rows.map((row) => (
                <div key={row.name}>
                  <b>{row.name}</b>
                  <i>{row.unclear ? "?" : "✓"}</i>
                </div>
              ))}
            </div>
            <i>Photo · 1.2 MB</i>
          </>
        )}
        {message.kind === "list" && (
          <>
            <b>{message.sw}</b>
            <i>{message.en}</i>
            <table className="wa-list">
              <tbody>
                {rows.map((row) => (
                  <tr key={row.name}>
                    <td className={row.unclear ? "unclear" : undefined}>
                      {row.name}
                      <span>{row.role}</span>
                    </td>
                    <td className={row.unclear ? "phone unclear" : "phone"}>{row.phone}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="wa-flag">
              <span aria-hidden="true" />
              Simu namba moja haieleweki — tafadhali angalia. <i>One phone number is unclear — please check.</i>
            </p>
          </>
        )}
        {message.kind === "text" && (
          <>
            <b>{message.sw}</b>
            <i>{message.en}</i>
          </>
        )}
        <Stamp />
      </div>
    </div>
  );
}

export function WhatsAppDemo({ replay = 0 }: { replay?: number }) {
  const panelRef = useRef<HTMLDivElement>(null);
  const timers = useRef<number[]>([]);
  const seen = useRef(false);
  const [shown, setShown] = useState(0);
  const [typing, setTyping] = useState(false);

  const clearTimers = useCallback(() => {
    timers.current.forEach((timer) => window.clearTimeout(timer));
    timers.current = [];
  }, []);

  const play = useCallback(() => {
    clearTimers();
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) {
      setShown(messages.length);
      setTyping(false);
      return;
    }
    setShown(0);
    setTyping(false);
    let at = 200;
    messages.forEach((message, index) => {
      if (message.from === "them") {
        timers.current.push(window.setTimeout(() => setTyping(true), at));
        at += 1100;
        timers.current.push(
          window.setTimeout(() => {
            setTyping(false);
            setShown(index + 1);
          }, at),
        );
        at += 450;
      } else {
        timers.current.push(
          window.setTimeout(() => {
            setShown(index + 1);
            setTyping(false);
          }, at),
        );
        at += 650;
      }
    });
  }, [clearTimers]);

  useEffect(() => {
    if (replay > 0) play();
  }, [replay, play]);

  useEffect(() => {
    const node = panelRef.current;
    if (!node || seen.current) return;
    if (!("IntersectionObserver" in window)) {
      seen.current = true;
      setShown(messages.length);
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          seen.current = true;
          play();
          observer.disconnect();
        }
      },
      { threshold: 0.25, rootMargin: "0px 0px -8% 0px" },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [play]);

  useEffect(() => clearTimers, [clearTimers]);

  const step = shown >= 4 ? 3 : shown >= 3 ? 2 : shown >= 1 ? 1 : 0;

  return (
    <div className="wa-shell">
      <div className="wa-device" ref={panelRef}>
        <span className="wa-speaker" aria-hidden="true" />
        <div className="wa-panel">
        <div className="wa-bar">
          <span className="wa-bar-id">
            <img src="/brand/digitali-mark.svg" alt="" aria-hidden="true" />
            <Wordmark inverse className="text-[1.35rem]" />
          </span>
          <span className="wa-status">online</span>
        </div>
        <div className="wa-body" aria-live="polite">
          {messages.slice(0, shown).map((message) => (
            <Bubble key={message.id} message={message} />
          ))}
          {typing && (
            <div className="wa-row">
              <div className="wa-bubble wa-typing" aria-label="Digitali is typing">
                <span aria-hidden="true" />
                <span aria-hidden="true" />
                <span aria-hidden="true" />
              </div>
            </div>
          )}
        </div>
        </div>
        <span className="wa-home" aria-hidden="true" />
      </div>
      <div className="wa-aside">
        <ol>
          <li className={step >= 1 ? "on" : undefined}>
            Piga picha — photograph the paper you already filled in.
          </li>
          <li className={step >= 2 ? "on" : undefined}>
            Tuma — Digitali reads it and sends back a list you can check.
          </li>
          <li className={step >= 3 ? "on" : undefined}>
            Pata orodha — you confirm, then keep it or download the data.
          </li>
        </ol>
        <div className="wa-controls">
          <button className="wa-replay" type="button" onClick={play}>
            <RotateCcw aria-hidden="true" /> Replay the conversation
          </button>
          <a className="text-link" href="#demo">
            Try it with your own photo <ArrowRight aria-hidden="true" />
          </a>
        </div>
      </div>
    </div>
  );
}
