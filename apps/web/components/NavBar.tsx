"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, AuthUser, githubLoginUrl } from "@/lib/api";

export default function NavBar() {
  const [user, setUser] = useState<AuthUser | null | undefined>(undefined);

  useEffect(() => {
    api
      .me()
      .then(setUser)
      .catch(() => setUser(null));
  }, []);

  async function logout() {
    await api.logout().catch(() => undefined);
    window.location.href = "/";
  }

  return (
    <header className="topbar">
      <Link href="/" className="brand">
        Wovn
      </Link>
      <nav>
        <Link href="/">Generate</Link>
        {user ? <Link href="/settings">Settings</Link> : null}
        {user === undefined ? null : user ? (
          <button type="button" className="secondary" onClick={logout}>
            Sign out {user.display_name}
          </button>
        ) : (
          <a className="btn" href={githubLoginUrl()}>
            Sign in with GitHub
          </a>
        )}
      </nav>
    </header>
  );
}
