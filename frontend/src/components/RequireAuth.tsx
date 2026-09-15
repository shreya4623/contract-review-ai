import { Navigate } from "react-router-dom";
import type { JSX } from "react";

export default function RequireAuth({ children }: { children: JSX.Element }) {
  const token = localStorage.getItem("access_token");
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return children;
}
