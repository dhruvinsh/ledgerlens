import type { ProcessingJob } from "@/lib/types";

type JobHandler = (job: ProcessingJob) => void;

class WSService {
  private ws: WebSocket | null = null;
  private handlers = new Set<JobHandler>();
  private reconnectDelay = 1000;
  private maxReconnectDelay = 30000;
  private sessionId: string | null = null;

  connect(sessionId: string): void {
    this.sessionId = sessionId;
    this.doConnect();
  }

  disconnect(): void {
    this.sessionId = null;
    this.ws?.close();
    this.ws = null;
  }

  subscribe(handler: JobHandler): () => void {
    this.handlers.add(handler);
    return () => this.handlers.delete(handler);
  }

  private doConnect(): void {
    if (!this.sessionId) return;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${protocol}//${window.location.host}/ws/jobs?session_id=${this.sessionId}`;

    this.ws = new WebSocket(url);

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data as string) as ProcessingJob;
        for (const handler of this.handlers) {
          handler(data);
        }
      } catch {
        // Ignore parse errors (e.g. pong messages)
      }
    };

    this.ws.onclose = () => {
      if (this.sessionId) {
        setTimeout(() => this.doConnect(), this.reconnectDelay);
        this.reconnectDelay = Math.min(
          this.reconnectDelay * 2,
          this.maxReconnectDelay,
        );
      }
    };

    this.ws.onopen = () => {
      this.reconnectDelay = 1000;
    };
  }
}

export const wsService = new WSService();
