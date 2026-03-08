import Link from "next/link";

export default function SiteFooter() {
  return (
    <footer className="border-t border-white/[0.06] bg-[#111118] px-6 py-8">
      <div className="max-w-6xl mx-auto">
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-6">
            <Link
              href="/"
              className="text-sm font-semibold text-zinc-400 hover:text-white transition-colors"
            >
              PropertyProfiler
            </Link>
            <Link
              href="/blog"
              className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
            >
              Blog
            </Link>
          </div>
          <p className="text-xs text-zinc-600">
            Queensland properties only &middot; Powered by GNAF &amp; QLD
            Cadastre
          </p>
        </div>
      </div>
    </footer>
  );
}
