import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { loginUser, registerUser, extractErrorMessage } from "../services/api";

export default function Login() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const auth = mode === "login" ? await loginUser(email, password) : await registerUser(email, password);
      localStorage.setItem("access_token", auth.access_token);
      localStorage.setItem("user_email", auth.email);
      navigate("/dashboard");
    } catch (err) {
      setError(extractErrorMessage(err, "Something went wrong. Please try again."));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-paper px-6">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <h1 className="font-serif text-2xl font-semibold text-ink">Clausewell</h1>
          <p className="mt-1 text-sm text-ink-soft">Contract review &amp; risk identification</p>
        </div>

        <div className="rounded-md border border-line bg-white p-6">
          <div className="mb-6 flex rounded-md border border-line p-1 text-sm">
            <button
              className={`flex-1 rounded py-1.5 transition-colors ${
                mode === "login" ? "bg-ink text-white" : "text-ink-soft"
              }`}
              onClick={() => setMode("login")}
              type="button"
            >
              Sign in
            </button>
            <button
              className={`flex-1 rounded py-1.5 transition-colors ${
                mode === "register" ? "bg-ink text-white" : "text-ink-soft"
              }`}
              onClick={() => setMode("register")}
              type="button"
            >
              Create account
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="mb-1 block text-sm text-ink-soft">Email</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded border border-line px-3 py-2 text-sm text-ink outline-none focus:border-brass"
                placeholder="you@company.com"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm text-ink-soft">Password</label>
              <input
                type="password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded border border-line px-3 py-2 text-sm text-ink outline-none focus:border-brass"
                placeholder="At least 8 characters"
              />
            </div>

            {error && <p className="text-sm text-risk-high">{error}</p>}

            <button
              type="submit"
              disabled={loading}
              className="w-full rounded bg-ink py-2.5 text-sm font-medium text-white transition-opacity hover:opacity-90 disabled:opacity-50"
            >
              {loading ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
            </button>
          </form>
        </div>

        <p className="mt-6 text-center text-xs text-ink-soft">
          This system provides contract-review support and does not constitute professional legal advice.
        </p>
      </div>
    </div>
  );
}
