import http from 'http';
import type { IncomingMessage, ServerResponse } from 'node:http';
import type { AddressInfo } from 'node:net';

export interface HealthServerOptions {
  host: string;
  port: number;
  infoProvider: () => object;
}

export class HealthServer {
  private readonly host: string;
  private readonly configuredPort: number;
  private readonly infoProvider: () => object;
  private listeningPort: number;
  private server: http.Server | null = null;

  constructor(options: HealthServerOptions) {
    this.host = options.host;
    this.configuredPort = options.port;
    this.infoProvider = options.infoProvider;
    this.listeningPort = options.port;
  }

  get port(): number {
    return this.listeningPort;
  }

  async start(): Promise<void> {
    if (this.server) {
      return;
    }

    this.server = http.createServer((req, res) => this.handleRequest(req, res));
    await new Promise<void>((resolve, reject) => {
      this.server!.once('error', reject);
      this.server!.listen(this.configuredPort, this.host, () => {
        const address = this.server!.address() as AddressInfo | null;
        this.listeningPort = address?.port ?? this.configuredPort;
        resolve();
      });
    });
  }

  async stop(): Promise<void> {
    if (!this.server) {
      return;
    }

    await new Promise<void>((resolve, reject) => {
      this.server!.close((error) => {
        if (error) {
          reject(error);
          return;
        }
        resolve();
      });
    });
    this.server = null;
  }

  private handleRequest(req: IncomingMessage, res: ServerResponse): void {
    if (req.url === '/health' || req.url === '/') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(this.infoProvider()));
      return;
    }

    if (req.url === '/ready') {
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ status: 'ready' }));
      return;
    }

    res.writeHead(404);
    res.end('Not found');
  }
}
