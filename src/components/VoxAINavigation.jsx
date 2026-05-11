import { Link, useLocation } from "wouter";

const items = [
  { href: "/", label: "Record" },
  { href: "/voxai", label: "Coach" },
  { href: "/history", label: "History" },
];

export default function VoxAINavigation() {
  const [location] = useLocation();

  return (
    <header className="sticky top-0 z-40 border-b border-border/40 bg-black/30 backdrop-blur-xl">
      <div className="container flex items-center justify-between py-4">
        <Link href="/" className="flex items-center gap-3">
          <img alt="Howard Vox AI" src="/images/howard-icon.png" className="h-10 w-10 rounded-xl object-cover" />
          <div>
            <div className="text-sm font-mono text-primary">HOWARD VOX AI</div>
            <div className="text-xs text-muted-foreground">Elite Vocal Analysis</div>
          </div>
        </Link>
        <nav className="flex items-center gap-2">
          {items.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={`rounded-full px-4 py-2 text-sm transition ${
                location === item.href ? "bg-primary/20 text-primary" : "text-muted-foreground hover:bg-white/5 hover:text-white"
              }`}
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
