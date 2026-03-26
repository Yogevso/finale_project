import type { ConnectionRegistrySnapshot } from './connectionRegistry.js';

type ConnectionRejectionReason = 'authentication_failed' | 'total_limit' | 'document_limit';
type SaturationStatus = 'normal' | 'elevated' | 'saturated';

interface DurationMetricState {
  readonly samples: number[];
  successCount: number;
  failureCount: number;
  lastSuccessAt: string | null;
  lastFailureAt: string | null;
  lastErrorType: string | null;
  lastErrorMessage: string | null;
}

interface DurationMetricSnapshot {
  sampleCount: number;
  successCount: number;
  failureCount: number;
  p50LatencyMs: number;
  p95LatencyMs: number;
  lastSuccessAt: string | null;
  lastFailureAt: string | null;
  lastErrorType: string | null;
  lastErrorMessage: string | null;
}

export interface CollabRuntimeMetricsConfig {
  maxTotalConnections: number;
  maxConnectionsPerDocument: number;
  reconnectWindowSeconds: number;
  elevatedUtilizationRatio?: number;
}

export interface CollabServerInfo {
  name: 'collab-server';
  status: 'healthy' | 'degraded';
  saturation: SaturationStatus;
  port: number;
  activeDocuments: number;
  totalConnections: number;
  uptime: number;
  guardrails: {
    maxTotalConnections: number;
    maxConnectionsPerDocument: number;
    totalConnectionUtilization: number;
    hottestDocumentUtilization: number;
    totalRejectedConnections: number;
    rejectionsByReason: Record<ConnectionRejectionReason, number>;
    lastRejectedAt: string | null;
    lastRejectedReason: ConnectionRejectionReason | null;
  };
  traffic: {
    totalAcceptedConnections: number;
    totalDisconnectedConnections: number;
    totalAuthenticationFailures: number;
    rapidReconnectsWithinWindow: number;
    reconnectWindowSeconds: number;
    lastAuthenticatedAt: string | null;
    lastDisconnectedAt: string | null;
  };
  documents: {
    maxConnectionsOnSingleDocument: number;
    topDocuments: ConnectionRegistrySnapshot['documents'];
  };
  persistence: {
    activeFailureDocuments: number;
    totalFailureEvents: number;
    totalRestoreEvents: number;
    lastFailureAt: string | null;
    lastFailedDocumentId: string | null;
    load: DurationMetricSnapshot;
    save: DurationMetricSnapshot;
  };
}

const MAX_DURATION_SAMPLES = 256;

function isoNow(): string {
  return new Date().toISOString();
}

function normalizeError(error: unknown): { type: string | null; message: string | null } {
  if (error instanceof Error) {
    return {
      type: error.name,
      message: error.message,
    };
  }

  if (typeof error === 'string') {
    return {
      type: 'Error',
      message: error,
    };
  }

  return {
    type: null,
    message: null,
  };
}

function percentile(samples: readonly number[], ratio: number): number {
  if (!samples.length) {
    return 0;
  }

  const ordered = [...samples].sort((left, right) => left - right);
  const index = Math.max(0, Math.min(ordered.length - 1, Math.ceil(ordered.length * ratio) - 1));
  return Number(ordered[index].toFixed(3));
}

function createDurationMetricState(): DurationMetricState {
  return {
    samples: [],
    successCount: 0,
    failureCount: 0,
    lastSuccessAt: null,
    lastFailureAt: null,
    lastErrorType: null,
    lastErrorMessage: null,
  };
}

function recordDuration(
  state: DurationMetricState,
  durationMs: number,
  success: boolean,
  error?: unknown,
): void {
  state.samples.push(Math.max(0, durationMs));
  if (state.samples.length > MAX_DURATION_SAMPLES) {
    state.samples.shift();
  }

  if (success) {
    state.successCount += 1;
    state.lastSuccessAt = isoNow();
    return;
  }

  state.failureCount += 1;
  state.lastFailureAt = isoNow();
  const normalizedError = normalizeError(error);
  state.lastErrorType = normalizedError.type;
  state.lastErrorMessage = normalizedError.message;
}

function snapshotDurationMetric(state: DurationMetricState): DurationMetricSnapshot {
  return {
    sampleCount: state.samples.length,
    successCount: state.successCount,
    failureCount: state.failureCount,
    p50LatencyMs: percentile(state.samples, 0.5),
    p95LatencyMs: percentile(state.samples, 0.95),
    lastSuccessAt: state.lastSuccessAt,
    lastFailureAt: state.lastFailureAt,
    lastErrorType: state.lastErrorType,
    lastErrorMessage: state.lastErrorMessage,
  };
}

export class CollabRuntimeMetrics {
  private readonly elevatedUtilizationRatio: number;
  private readonly reconnectWindowMs: number;
  private readonly lastDisconnectByUserDocument = new Map<string, number>();
  private readonly loadDurations = createDurationMetricState();
  private readonly saveDurations = createDurationMetricState();
  private readonly activeFailureDocuments = new Set<string>();
  private readonly rejectionsByReason: Record<ConnectionRejectionReason, number> = {
    authentication_failed: 0,
    total_limit: 0,
    document_limit: 0,
  };

  private totalAcceptedConnections = 0;
  private totalDisconnectedConnections = 0;
  private totalAuthenticationFailures = 0;
  private totalRejectedConnections = 0;
  private rapidReconnectsWithinWindow = 0;
  private totalPersistenceFailureEvents = 0;
  private totalPersistenceRestoreEvents = 0;
  private lastAuthenticatedAt: string | null = null;
  private lastDisconnectedAt: string | null = null;
  private lastRejectedAt: string | null = null;
  private lastRejectedReason: ConnectionRejectionReason | null = null;
  private lastFailureAt: string | null = null;
  private lastFailedDocumentId: string | null = null;

  constructor(private readonly config: CollabRuntimeMetricsConfig) {
    this.elevatedUtilizationRatio = Math.max(
      0.1,
      Math.min(0.99, config.elevatedUtilizationRatio ?? 0.8),
    );
    this.reconnectWindowMs = Math.max(1, config.reconnectWindowSeconds) * 1000;
  }

  recordConnectionAccepted(params: { documentId: string; userId: string }): void {
    const reconnectKey = `${params.documentId}:${params.userId}`;
    const now = Date.now();
    const lastDisconnectAt = this.lastDisconnectByUserDocument.get(reconnectKey);
    if (typeof lastDisconnectAt === 'number' && now - lastDisconnectAt <= this.reconnectWindowMs) {
      this.rapidReconnectsWithinWindow += 1;
    }

    this.totalAcceptedConnections += 1;
    this.lastAuthenticatedAt = isoNow();
  }

  recordConnectionDisconnected(params: { documentId: string; userId?: string | null }): void {
    this.totalDisconnectedConnections += 1;
    this.lastDisconnectedAt = isoNow();

    if (params.userId) {
      this.lastDisconnectByUserDocument.set(
        `${params.documentId}:${params.userId}`,
        Date.now(),
      );
    }
  }

  recordConnectionRejected(reason: ConnectionRejectionReason): void {
    this.totalRejectedConnections += 1;
    this.rejectionsByReason[reason] += 1;
    this.lastRejectedAt = isoNow();
    this.lastRejectedReason = reason;
  }

  recordAuthenticationFailure(): void {
    this.totalAuthenticationFailures += 1;
    this.recordConnectionRejected('authentication_failed');
  }

  recordDocumentLoad(params: { durationMs: number; success: boolean; error?: unknown }): void {
    recordDuration(this.loadDurations, params.durationMs, params.success, params.error);
  }

  recordDocumentSave(params: { durationMs: number; success: boolean; error?: unknown }): void {
    recordDuration(this.saveDurations, params.durationMs, params.success, params.error);
  }

  recordPersistenceFailure(documentId: string): void {
    this.totalPersistenceFailureEvents += 1;
    this.lastFailureAt = isoNow();
    this.lastFailedDocumentId = documentId;
    this.activeFailureDocuments.add(documentId);
  }

  recordPersistenceRestored(documentId: string): void {
    if (this.activeFailureDocuments.delete(documentId)) {
      this.totalPersistenceRestoreEvents += 1;
    }
  }

  snapshot(params: {
    port: number;
    uptime: number;
    registry: ConnectionRegistrySnapshot;
  }): CollabServerInfo {
    const totalConnectionUtilization = params.registry.totalConnections / this.config.maxTotalConnections;
    const hottestDocumentUtilization =
      params.registry.maxConnectionsOnSingleDocument / this.config.maxConnectionsPerDocument;

    let saturation: SaturationStatus = 'normal';
    if (totalConnectionUtilization >= 1 || hottestDocumentUtilization >= 1) {
      saturation = 'saturated';
    } else if (
      totalConnectionUtilization >= this.elevatedUtilizationRatio ||
      hottestDocumentUtilization >= this.elevatedUtilizationRatio
    ) {
      saturation = 'elevated';
    }

    return {
      name: 'collab-server',
      status:
        saturation === 'saturated' || this.activeFailureDocuments.size > 0 ? 'degraded' : 'healthy',
      saturation,
      port: params.port,
      activeDocuments: params.registry.activeDocuments,
      totalConnections: params.registry.totalConnections,
      uptime: params.uptime,
      guardrails: {
        maxTotalConnections: this.config.maxTotalConnections,
        maxConnectionsPerDocument: this.config.maxConnectionsPerDocument,
        totalConnectionUtilization: Number(totalConnectionUtilization.toFixed(3)),
        hottestDocumentUtilization: Number(hottestDocumentUtilization.toFixed(3)),
        totalRejectedConnections: this.totalRejectedConnections,
        rejectionsByReason: { ...this.rejectionsByReason },
        lastRejectedAt: this.lastRejectedAt,
        lastRejectedReason: this.lastRejectedReason,
      },
      traffic: {
        totalAcceptedConnections: this.totalAcceptedConnections,
        totalDisconnectedConnections: this.totalDisconnectedConnections,
        totalAuthenticationFailures: this.totalAuthenticationFailures,
        rapidReconnectsWithinWindow: this.rapidReconnectsWithinWindow,
        reconnectWindowSeconds: this.config.reconnectWindowSeconds,
        lastAuthenticatedAt: this.lastAuthenticatedAt,
        lastDisconnectedAt: this.lastDisconnectedAt,
      },
      documents: {
        maxConnectionsOnSingleDocument: params.registry.maxConnectionsOnSingleDocument,
        topDocuments: params.registry.documents,
      },
      persistence: {
        activeFailureDocuments: this.activeFailureDocuments.size,
        totalFailureEvents: this.totalPersistenceFailureEvents,
        totalRestoreEvents: this.totalPersistenceRestoreEvents,
        lastFailureAt: this.lastFailureAt,
        lastFailedDocumentId: this.lastFailedDocumentId,
        load: snapshotDurationMetric(this.loadDurations),
        save: snapshotDurationMetric(this.saveDurations),
      },
    };
  }
}
