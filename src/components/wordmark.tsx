import { cn } from "@/lib/utils";

const dropPath = "M50,0 C59,40 100,57 100,90 A50,50 0 0 1 0,90 C0,57 41,40 50,0 Z";

function DottedI() {
  return (
    <span className="relative inline-block">
      ı
      <svg
        aria-hidden="true"
        viewBox="0 0 100 140"
        className="absolute left-1/2 top-[0.02em] h-[0.19em] w-[0.14em] -translate-x-1/2 overflow-visible text-manjano"
      >
        <path d={dropPath} fill="currentColor" />
      </svg>
    </span>
  );
}

export function Wordmark({ inverse = false, className }: { inverse?: boolean; className?: string }) {
  return (
    <span
      aria-label="digitali"
      className={cn(
        "font-display text-[2rem] font-medium leading-none tracking-normal",
        inverse ? "text-primary-foreground" : "text-foreground",
        className,
      )}
    >
      d<DottedI />g<DottedI />tal<DottedI />
    </span>
  );
}

export function BrandLockup({ inverse = false }: { inverse?: boolean }) {
  return (
    <span className="inline-flex items-end gap-3">
      <img src="/brand/digitali-mark.svg" alt="" className="h-8 w-6" />
      <Wordmark inverse={inverse} />
    </span>
  );
}

export function DropRow() {
  return (
    <span aria-hidden="true" className="flex justify-center gap-5 text-manjano">
      {[0, 1, 2, 3, 4].map((drop) => (
        <svg key={drop} viewBox="0 0 100 140" className="h-3 w-2">
          <path d={dropPath} fill="currentColor" />
        </svg>
      ))}
    </span>
  );
}
