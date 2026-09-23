import { useRef, useState } from "react";
import { Download, RotateCcw, Upload } from "lucide-react";
import { Button } from "@/components/ui/button";
import { extractAttendance, type ExtractedRecord } from "@/lib/extract.functions";

const starterRows: ExtractedRecord[] = [
  { name: "Amina Hassan", role: "Treasurer", phone: "0712 440 983", signed: true, lowConfidence: [] },
  { name: "Neema Juma", role: "Member", phone: "0754 120 648", signed: true, lowConfidence: [] },
  { name: "Rehema Ali", role: "Member", phone: "0788 39? 211", signed: false, lowConfidence: ["phone"] },
  { name: "Fatma Said", role: "Secretary", phone: "0741 602 457", signed: true, lowConfidence: [] },
];

function fileToDataUrl(file: File) {
  return new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => typeof reader.result === "string" ? resolve(reader.result) : reject(new Error("Could not read photo."));
    reader.onerror = () => reject(new Error("Could not read photo."));
    reader.readAsDataURL(file);
  });
}

export function PhotoDemo() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [rows, setRows] = useState(starterRows);
  const [preview, setPreview] = useState<string>();
  const [extractionPrompt, setExtractionPrompt] = useState("");
  const [status, setStatus] = useState<"ready" | "reading" | "review">("ready");
  const [error, setError] = useState<string>();
  const [source, setSource] = useState<string>();

  async function handleFile(file?: File) {
    if (!file) return;
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      setError("Please choose a JPG, PNG or WebP photo.");
      return;
    }
    if (file.size > 7_000_000) {
      setError("Please choose a photo smaller than 7 MB.");
      return;
    }
    setError(undefined);
    setStatus("reading");
    const dataUrl = await fileToDataUrl(file);
    setPreview(dataUrl);
    try {
      const result = await extractAttendance({
        data: {
          dataUrl,
          mimeType: file.type as "image/jpeg" | "image/png" | "image/webp",
          prompt: extractionPrompt.trim() || undefined,
        },
      });
      setRows(result.records);
      setSource(result.source);
      setStatus("review");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "We could not read that photo. Please try again.");
      setStatus("ready");
    }
  }

  function updateCell(index: number, field: "name" | "role" | "phone", value: string) {
    setRows((current) => current.map((row, rowIndex) => rowIndex === index ? {
      ...row,
      [field]: value,
      lowConfidence: row.lowConfidence.filter((item) => item !== field),
    } : row));
  }

  function downloadJson() {
    const blob = new Blob([JSON.stringify({ records: rows }, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "digitali-attendance.json";
    anchor.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="demo-shell">
      <div className="demo-photo">
        {preview ? <img src={preview} alt="Your uploaded paper record" /> : (
          <div className="paper-sheet" aria-label="Example handwritten attendance sheet">
            <p>Jumuiya ya Tumaini</p><span>Meeting attendance · 14 June</span>
            {starterRows.map((row) => <div key={row.name}><b>{row.name}</b><i>{row.signed ? "✓" : "—"}</i></div>)}
          </div>
        )}
        <label className="extraction-request">
          <span>What should we look for? <small>Optional</small></span>
          <textarea
            value={extractionPrompt}
            onChange={(event) => setExtractionPrompt(event.target.value)}
            placeholder="tell us what data you want extracted"
            maxLength={500}
            rows={3}
            disabled={status === "reading"}
          />
        </label>
        <input ref={inputRef} className="sr-only" type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => void handleFile(event.target.files?.[0])} />
        <Button variant="outline" size="lg" onClick={() => inputRef.current?.click()} disabled={status === "reading"}>
          <Upload aria-hidden="true" /> {status === "reading" ? "Reading your photo…" : "Choose a photo"}
        </Button>
        <p>JPG, PNG or WebP · up to 7 MB</p>
      </div>
      <div className="demo-result" aria-live="polite">
        <div className="demo-heading">
          <div><span className="eyebrow">Your clean list</span><h3>{status === "review" ? "Ready for your review" : "Attendance register"}</h3></div>
          {preview && <Button variant="ghost" size="icon" aria-label="Reset demo" title="Reset demo" onClick={() => { setPreview(undefined); setRows(starterRows); setStatus("ready"); setError(undefined); }}><RotateCcw /></Button>}
        </div>
        {error && <p className="demo-error">{error}</p>}
        <div className="table-wrap">
          <table>
            <thead><tr><th>Name</th><th>Role</th><th>Phone</th><th>Signed</th></tr></thead>
            <tbody>{rows.map((row, index) => <tr key={`${index}-${row.name}`}>
              {(["name", "role", "phone"] as const).map((field) => <td key={field} className={row.lowConfidence.includes(field) ? "unclear" : undefined}><input aria-label={`${field} for row ${index + 1}`} value={row[field]} onChange={(event) => updateCell(index, field, event.target.value)} /></td>)}
              <td><input aria-label={`Signed for row ${index + 1}`} type="checkbox" checked={row.signed} onChange={(event) => setRows((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, signed: event.target.checked, lowConfidence: item.lowConfidence.filter((field) => field !== "signed") } : item))} /></td>
            </tr>)}</tbody>
          </table>
        </div>
        <p className="check-note"><span />We ask you to check anything we couldn't read.</p>
        {status === "review" && source && <p className="source-note">{source}</p>}
        <Button size="lg" onClick={downloadJson}><Download aria-hidden="true" /> Confirm and download</Button>
      </div>
    </div>
  );
}
