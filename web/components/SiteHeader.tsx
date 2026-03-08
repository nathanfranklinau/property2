import Link from "next/link";

export default function SiteHeader() {
  return (
    <header className="border-b border-white/[0.06] bg-[#111118] px-6 py-4">
      <nav className="max-w-6xl mx-auto flex items-center justify-between">
        <Link
          href="/"
          className="font-semibold text-white text-base tracking-tight hover:text-zinc-300 transition-colors"
        >
          PropertyProfiler
        </Link>
        <div className="flex items-center gap-6">
          <Link
            href="/blog"
            className="text-sm text-zinc-400 hover:text-white transition-colors"
          >
            Blog
          </Link>
        </div>
      </nav>
    </header>
  );
}
