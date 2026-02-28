import http from 'http';

import { HealthServer } from '../server/healthServer.js';

function getJson(url: string): Promise<{ status: number; body: unknown }> {
  return new Promise((resolve, reject) => {
    http
      .get(url, (res) => {
        const chunks: Buffer[] = [];
        res.on('data', (chunk) => chunks.push(Buffer.from(chunk)));
        res.on('end', () => {
          const raw = Buffer.concat(chunks).toString('utf-8');
          const body = raw ? JSON.parse(raw) : null;
          resolve({ status: res.statusCode || 0, body });
        });
      })
      .on('error', reject);
  });
}

function getText(url: string): Promise<{ status: number; body: string }> {
  return new Promise((resolve, reject) => {
    http
      .get(url, (res) => {
        const chunks: Buffer[] = [];
        res.on('data', (chunk) => chunks.push(Buffer.from(chunk)));
        res.on('end', () => {
          resolve({
            status: res.statusCode || 0,
            body: Buffer.concat(chunks).toString('utf-8'),
          });
        });
      })
      .on('error', reject);
  });
}

describe('HealthServer', () => {
  it('serves health and readiness endpoints', async () => {
    const healthServer = new HealthServer({
      host: '127.0.0.1',
      port: 0,
      infoProvider: () => ({ status: 'healthy', activeDocuments: 2 }),
    });

    await healthServer.start();
    const baseUrl = `http://127.0.0.1:${healthServer.port}`;

    const health = await getJson(`${baseUrl}/health`);
    expect(health.status).toBe(200);
    expect(health.body).toMatchObject({ status: 'healthy', activeDocuments: 2 });

    const ready = await getJson(`${baseUrl}/ready`);
    expect(ready.status).toBe(200);
    expect(ready.body).toMatchObject({ status: 'ready' });

    const notFound = await getText(`${baseUrl}/unknown`);
    expect(notFound.status).toBe(404);
    expect(notFound.body).toBe('Not found');

    await healthServer.stop();
  });
});
