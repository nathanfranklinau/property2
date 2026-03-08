import Link from "next/link";
import type { Metadata } from "next";
import {
  getAllPosts,
  categoryLabel,
  type BlogCategory,
} from "@/lib/blog";

export const metadata: Metadata = {
  title: "Blog — PropertyProfiler",
  description:
    "Property insights, subdivision guides, zoning explainers, and tips for Queensland homeowners.",
};

const CATEGORIES: { id: BlogCategory | "all"; label: string }[] = [
  { id: "all", label: "All" },
  { id: "subdivision", label: "Subdivision" },
  { id: "zoning", label: "Zoning" },
  { id: "property-tips", label: "Property Tips" },
  { id: "council-guides", label: "Council Guides" },
];

export default async function BlogIndex({
  searchParams,
}: {
  searchParams: Promise<{ category?: string }>;
}) {
  const { category: filterCat } = await searchParams;
  const posts = getAllPosts();
  const filtered =
    filterCat && filterCat !== "all"
      ? posts.filter((p) => p.category === filterCat)
      : posts;

  return (
    <div className="max-w-3xl mx-auto px-6 py-16">
      <h1 className="text-3xl font-bold text-white tracking-tight mb-2">
        Blog
      </h1>
      <p className="text-zinc-400 text-base mb-10">
        Guides and insights for Queensland property owners.
      </p>

      {/* Category filter */}
      <div className="flex flex-wrap gap-2 mb-10">
        {CATEGORIES.map((cat) => {
          const active =
            cat.id === "all"
              ? !filterCat || filterCat === "all"
              : filterCat === cat.id;
          return (
            <Link
              key={cat.id}
              href={
                cat.id === "all" ? "/blog" : `/blog?category=${cat.id}`
              }
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                active
                  ? "bg-white/[0.1] text-white"
                  : "text-zinc-500 hover:text-zinc-300 hover:bg-white/[0.04]"
              }`}
            >
              {cat.label}
            </Link>
          );
        })}
      </div>

      {/* Post list */}
      {filtered.length === 0 ? (
        <p className="text-zinc-500 text-sm">No posts yet in this category.</p>
      ) : (
        <div className="space-y-8">
          {filtered.map((post) => (
            <article key={post.slug}>
              <Link href={`/blog/${post.slug}`} className="group block">
                <div className="flex items-center gap-3 mb-1.5">
                  <span className="text-[10px] font-semibold uppercase tracking-widest text-emerald-400">
                    {categoryLabel(post.category)}
                  </span>
                  <span className="text-[10px] text-zinc-600">
                    {formatDate(post.date)}
                  </span>
                </div>
                <h2 className="text-lg font-semibold text-white group-hover:text-emerald-400 transition-colors leading-snug">
                  {post.title}
                </h2>
                {post.description && (
                  <p className="text-sm text-zinc-400 mt-1 leading-relaxed">
                    {post.description}
                  </p>
                )}
              </Link>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}

function formatDate(dateStr: string): string {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-AU", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}
