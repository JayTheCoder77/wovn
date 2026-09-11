import "./globals.css";
import Link from "next/link";

export const metadata = {
  title: "Wovn",
  description: "Weave a documentation site from a GitHub repo — static analysis, BYOK Groq.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="topbar">
          <Link href="/" className="brand">
            Wovn
          </Link>
          <nav>
            <Link href="/">Generate</Link>
            <Link href="/settings">Settings</Link>
          </nav>
        </header>
        {children}
      </body>
    </html>
  );
}
