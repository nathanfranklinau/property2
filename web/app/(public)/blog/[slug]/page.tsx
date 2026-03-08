import { notFound } from "next/navigation";
import type { Metadata } from "next";
import Link from "next/link";
import { MDXRemote } from "next-mdx-remote/rsc";
import {
  getAllSlugs,
  getPostBySlug,
  categoryLabel,
} from "@/lib/blog";

type Params = { slug: string };

export async function generateStaticParams(): Promise<Params[]> {
  return getAllSlugs().map((slug) => ({ slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<Params>;
}): Promise<Metadata> {
  const { slug } = await params;
  const post = getPostBySlug(slug);
  if (!post) return {};
  return {
    title: `${post.title} — PropertyProfiler`,
    description: post.description,
  };
}

export default async function BlogPostPage({
  params,
}: {
  params: Promise<Params>;
}) {
  const { slug } = await params;
  const post = getPostBySlug(slug);
  if (!post) notFound();

  const date = post.date
    ? new Date(post.date).toLocaleDateString("en-AU", {
        day: "numeric",
        month: "long",
        year: "numeric",
      })
    : null;

  return (
    <article className="max-w-2xl mx-auto px-6 py-16">
      <Link
        href="/blog"
        className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors mb-8 inline-flex items-center gap-1"
      >
        <svg
          className="w-3 h-3"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path d="M19 12H5M12 19l-7-7 7-7" />
        </svg>
        Back to blog
      </Link>

      <div className="flex items-center gap-3 mb-4 mt-6">
        <span className="text-[10px] font-semibold uppercase tracking-widest text-emerald-400">
          {categoryLabel(post.category)}
        </span>
        {date && <span className="text-[10px] text-zinc-600">{date}</span>}
      </div>

      <h1 className="text-3xl font-bold text-white tracking-tight leading-tight mb-8">
        {post.title}
      </h1>

      <div className="prose prose-invert prose-zinc prose-sm max-w-none prose-headings:text-white prose-headings:font-semibold prose-p:text-zinc-300 prose-a:text-emerald-400 prose-a:no-underline hover:prose-a:underline prose-strong:text-white prose-li:text-zinc-300 prose-hr:border-white/10">
        <MDXRemote source={post.content} />
      </div>
    </article>
  );
}
