import "./globals.css";
import NavBar from "@/components/NavBar";

export const metadata = {
  title: "Wovn",
  description: "Weave a documentation site from a GitHub repo — static analysis, BYOK Groq.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <NavBar />
        {children}
      </body>
    </html>
  );
}
