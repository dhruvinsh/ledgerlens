type JobUpdateHandler = (data: Record<string, unknown>) => void;

class WSService {
  private ws: WebSocket | null = null;
  private handlers = new Set<JobUpdateHandler>();
  private reconnectDelay = 1000;
  private maxReconnectDelay = 30000;
  private active = false;

  connect(): void {
    if (this.active) return;
    this.active = true;
    this.doConnect();
  }

  disconnect(): void {
    this.active = false;
    this.ws?.close();
    this.ws = null;
  }

  subscribe(handler: JobUpdateHandler): () => void {
    this.handlers.add(handler);
    return () => this.handlers.delete(handler);
  }

  private doConnect(): void {
    if (!this.active) return;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${protocol}//${window.location.host}/ws/jobs`;

    this.ws = new WebSocket(url);

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data as string) as Record<string, unknown>;
        for (const handler of this.handlers) {
          handler(data);
        }
      } catch {
        // Ignore parse errors (e.g. pong messages)
      }
    };

    this.ws.onclose = () => {
      if (this.active) {
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
