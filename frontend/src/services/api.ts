class ApiClient {
  private baseUrl = "/api/v1";

  private async request<T>(
    method: string,
    path: string,
    options?: { body?: unknown; params?: Record<string, string> },
  ): Promise<T> {
    const url = new URL(`${this.baseUrl}${path}`, window.location.origin);
    if (options?.params) {
      for (const [key, value] of Object.entries(options.params)) {
        if (value !== undefined && value !== "") {
          url.searchParams.set(key, value);
        }
      }
    }

    const headers: HeadersInit = {};
    let body: BodyInit | undefined;

    if (options?.body && !(options.body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
      body = JSON.stringify(options.body);
    } else if (options?.body instanceof FormData) {
      body = options.body;
    }

    const res = await fetch(url.toString(), {
      method,
      headers,
      body,
      credentials: "include",
    });

    if (res.status === 401 && !path.startsWith("/auth")) {
      window.location.href = "/login";
      throw new Error("Unauthorized");
    }

    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: "Request failed" }));
      throw new Error(error.detail ?? "Request failed");
    }

    if (res.status === 204) return undefined as T;
    return res.json() as Promise<T>;
  }

  get<T>(path: string, params?: Record<string, string>): Promise<T> {
    return this.request<T>("GET", path, { params });
  }

  post<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>("POST", path, { body });
  }

  patch<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>("PATCH", path, { body });
  }

  delete<T>(path: string): Promise<T> {
    return this.request<T>("DELETE", path);
  }

  upload<T>(path: string, formData: FormData): Promise<T> {
    return this.request<T>("POST", path, { body: formData });
  }

  uploadWithProgress<T>(
    path: string,
    formData: FormData,
    onProgress?: (pct: number) => void,
  ): Promise<T> {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", `${this.baseUrl}${path}`);
      xhr.withCredentials = true;

      if (onProgress) {
        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable)
            onProgress(Math.round((e.loaded / e.total) * 100));
        };
      }

      xhr.onload = () => {
        if (xhr.status === 401) {
          window.location.href = "/login";
          return reject(new Error("Unauthorized"));
        }
        try {
          const data = JSON.parse(xhr.responseText);
          if (xhr.status >= 200 && xhr.status < 300) {
            return resolve(data as T);
          }
          return reject(new Error(data.detail ?? "Upload failed"));
        } catch {
          return reject(new Error("Failed to parse server response"));
        }
      };

      xhr.onerror = () => reject(new Error("Network error"));
      xhr.send(formData);
    });
  }
}

export const api = new ApiClient();
