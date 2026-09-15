import axios from "axios";
import type {
  DocumentResponse,
  ReviewListItem,
  ReviewResponse,
} from "../types/review";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: API_BASE_URL,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("access_token");
      localStorage.removeItem("user_email");
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

export interface AuthResponse {
  access_token: string;
  token_type: string;
  email: string;
}

export async function registerUser(email: string, password: string) {
  const { data } = await api.post<AuthResponse>("/auth/register", { email, password });
  return data;
}

export async function loginUser(email: string, password: string) {
  const { data } = await api.post<AuthResponse>("/auth/login", { email, password });
  return data;
}

export async function uploadDocument(
  file: File,
  documentType: "contract" | "reference"
) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("document_type", documentType);

  const { data } = await api.post<DocumentResponse>("/documents/upload", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function createReview(contractId: string, referenceId: string) {
  const { data } = await api.post<ReviewResponse>("/reviews", {
    contract_document_id: contractId,
    reference_document_id: referenceId,
  });
  return data;
}

export async function listReviews() {
  const { data } = await api.get<ReviewListItem[]>("/reviews");
  return data;
}

export async function getReview(reviewId: string) {
  const { data } = await api.get<ReviewResponse>(`/reviews/${reviewId}`);
  return data;
}

function extractErrorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
  }
  return fallback;
}

export { extractErrorMessage };
