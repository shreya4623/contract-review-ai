import { Link, useLocation, useNavigate } from "react-router-dom";

export default function Navbar() {
  const location = useLocation();
  const navigate = useNavigate();
  const email = localStorage.getItem("user_email");

  const isActive = (path: string) => location.pathname === path;

  function handleLogout() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("user_email");
    navigate("/login");
  }

  if (!email) return null;

  return (
    <header className="border-b border-line bg-paper">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link to="/dashboard" className="flex items-baseline gap-2">
          <span className="font-serif text-lg font-semibold text-ink">Clausewell</span>
          <span className="hidden text-xs text-ink-soft sm:inline">contract review support</span>
        </Link>

        <nav className="flex items-center gap-6 text-sm">
          <Link
            to="/dashboard"
            className={`transition-colors ${
              isActive("/dashboard") ? "text-ink font-medium" : "text-ink-soft hover:text-ink"
            }`}
          >
            Dashboard
          </Link>
          <Link
            to="/upload"
            className={`transition-colors ${
              isActive("/upload") ? "text-ink font-medium" : "text-ink-soft hover:text-ink"
            }`}
          >
            New Review
          </Link>
          <div className="flex items-center gap-3 border-l border-line pl-6">
            <span className="text-ink-soft">{email}</span>
            <button
              onClick={handleLogout}
              className="rounded border border-line px-3 py-1.5 text-ink-soft transition-colors hover:border-ink hover:text-ink"
            >
              Sign out
            </button>
          </div>
        </nav>
      </div>
    </header>
  );
}
