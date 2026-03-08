import fs from "fs";
import path from "path";
import matter from "gray-matter";

export type BlogCategory =
  | "subdivision"
  | "zoning"
  | "property-tips"
  | "council-guides";

export type BlogPost = {
  slug: string;
  title: string;
  date: string;
  category: BlogCategory;
  description: string;
  content: string;
};

const BLOG_DIR = path.join(process.cwd(), "content", "blog");

export function getAllPosts(): BlogPost[] {
  if (!fs.existsSync(BLOG_DIR)) return [];

  const files = fs
    .readdirSync(BLOG_DIR)
    .filter((f) => f.endsWith(".mdx"));

  const posts = files.map((filename) => {
    const slug = filename.replace(/\.mdx$/, "");
    const raw = fs.readFileSync(path.join(BLOG_DIR, filename), "utf-8");
    const { data, content } = matter(raw);
    return {
      slug,
      title: data.title ?? slug,
      date: data.date ?? "",
      category: (data.category ?? "property-tips") as BlogCategory,
      description: data.description ?? "",
      content,
    };
  });

  return posts.sort(
    (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()
  );
}

export function getPostBySlug(slug: string): BlogPost | null {
  const filePath = path.join(BLOG_DIR, `${slug}.mdx`);
  if (!fs.existsSync(filePath)) return null;

  const raw = fs.readFileSync(filePath, "utf-8");
  const { data, content } = matter(raw);
  return {
    slug,
    title: data.title ?? slug,
    date: data.date ?? "",
    category: (data.category ?? "property-tips") as BlogCategory,
    description: data.description ?? "",
    content,
  };
}

export function getAllSlugs(): string[] {
  if (!fs.existsSync(BLOG_DIR)) return [];
  return fs
    .readdirSync(BLOG_DIR)
    .filter((f) => f.endsWith(".mdx"))
    .map((f) => f.replace(/\.mdx$/, ""));
}

const CATEGORY_LABELS: Record<BlogCategory, string> = {
  subdivision: "Subdivision",
  zoning: "Zoning",
  "property-tips": "Property Tips",
  "council-guides": "Council Guides",
};

export function categoryLabel(cat: BlogCategory): string {
  return CATEGORY_LABELS[cat] ?? cat;
}
