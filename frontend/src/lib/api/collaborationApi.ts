import type { ApiHttpClient, Constructor } from './httpClient'
import {
  type CollaborationActiveSessionsResponseDto,
  type CollaborationActivityFeedResponseDto,
  type CollaborationAutoSnapshotResponseDto,
  type CollaborationRestoreSnapshotResponseDto,
  type CollaborationSessionStartResponseDto,
  type CollaborationSnapshotDto,
  type CollaborationSnapshotListResponseDto,
  type CollaborationStatusResponseDto,
  type CollaborationTokenResponseDto,
  mapCollaborationActiveSessionsResponseDto,
  mapCollaborationActivityFeedResponseDto,
  mapCollaborationAutoSnapshotResponseDto,
  mapCollaborationRestoreSnapshotResponseDto,
  mapCollaborationSessionStartResponseDto,
  mapCollaborationSnapshotDto,
  mapCollaborationSnapshotListResponseDto,
  mapCollaborationStatusResponseDto,
  mapCollaborationTokenResponseDto,
} from './dto'

export const CollaborationApiMixin = <TBase extends Constructor<ApiHttpClient>>(Base: TBase) =>
  class extends Base {
    constructor(...args: any[]) {
      super(...args)
    }

    async getCollabToken(documentId: number): Promise<CollaborationTokenResponseDto> {
      const { data } = await this.client.post<CollaborationTokenResponseDto>('/auth/collab-token', {
        document_id: documentId,
      })
      return mapCollaborationTokenResponseDto(data)
    }

    async getCollaborationStatus(
      documentId: number,
    ): Promise<CollaborationStatusResponseDto> {
      const { data } = await this.client.get<CollaborationStatusResponseDto>(
        `/collaboration/documents/${documentId}/status`,
      )
      return mapCollaborationStatusResponseDto(data)
    }

    async startCollaborationSession(
      documentId: number,
    ): Promise<CollaborationSessionStartResponseDto> {
      const { data } = await this.client.post<CollaborationSessionStartResponseDto>(
        '/collaboration/sessions/start',
        {
        document_id: documentId,
        },
      )
      return mapCollaborationSessionStartResponseDto(data)
    }

    async endCollaborationSession(sessionId: string, editsCount: number = 0): Promise<void> {
      await this.client.post('/collaboration/sessions/end', {
        session_id: sessionId,
        edits_count: editsCount,
      })
    }

    async logCollaborationActivity(
      documentId: number,
      activityType: string,
      sessionId?: string,
      details?: Record<string, unknown>,
    ): Promise<void> {
      await this.client.post('/collaboration/activity', {
        document_id: documentId,
        activity_type: activityType,
        session_id: sessionId,
        details,
      })
    }

    async getActivityFeed(
      documentId: number,
      limit: number = 50,
      offset: number = 0,
    ): Promise<CollaborationActivityFeedResponseDto> {
      const { data } = await this.client.get<CollaborationActivityFeedResponseDto>(
        `/collaboration/documents/${documentId}/activity`,
        {
          params: { limit, offset },
        },
      )
      return mapCollaborationActivityFeedResponseDto(data)
    }

    async getActiveSessions(documentId: number): Promise<CollaborationActiveSessionsResponseDto> {
      const { data } = await this.client.get<CollaborationActiveSessionsResponseDto>(
        `/collaboration/documents/${documentId}/sessions`,
      )
      return mapCollaborationActiveSessionsResponseDto(data)
    }

    async createSnapshot(
      documentId: number,
      options?: { name?: string; description?: string; session_id?: string },
    ): Promise<CollaborationSnapshotDto> {
      const { data } = await this.client.post<CollaborationSnapshotDto>(
        `/collaboration/documents/${documentId}/snapshots`,
        options || {},
      )
      return mapCollaborationSnapshotDto(data)
    }

    async listSnapshots(
      documentId: number,
      options?: { limit?: number; offset?: number; include_expired?: boolean },
    ): Promise<CollaborationSnapshotListResponseDto> {
      const { data } = await this.client.get<CollaborationSnapshotListResponseDto>(
        `/collaboration/documents/${documentId}/snapshots`,
        {
          params: options,
        },
      )
      return mapCollaborationSnapshotListResponseDto(data)
    }

    async getSnapshot(documentId: number, snapshotId: number): Promise<CollaborationSnapshotDto> {
      const { data } = await this.client.get<CollaborationSnapshotDto>(
        `/collaboration/documents/${documentId}/snapshots/${snapshotId}`,
      )
      return mapCollaborationSnapshotDto(data)
    }

    async restoreSnapshot(
      documentId: number,
      snapshotId: number,
      sessionId?: string,
    ): Promise<CollaborationRestoreSnapshotResponseDto> {
      const { data } = await this.client.post<CollaborationRestoreSnapshotResponseDto>(
        `/collaboration/documents/${documentId}/snapshots/${snapshotId}/restore`,
        { session_id: sessionId },
      )
      return mapCollaborationRestoreSnapshotResponseDto(data)
    }

    async updateSnapshot(
      documentId: number,
      snapshotId: number,
      updates: { name?: string; description?: string; is_pinned?: boolean },
    ): Promise<CollaborationSnapshotDto> {
      const { data } = await this.client.patch<CollaborationSnapshotDto>(
        `/collaboration/documents/${documentId}/snapshots/${snapshotId}`,
        updates,
      )
      return mapCollaborationSnapshotDto(data)
    }

    async deleteSnapshot(documentId: number, snapshotId: number): Promise<void> {
      await this.client.delete(`/collaboration/documents/${documentId}/snapshots/${snapshotId}`)
    }

    async createAutoSnapshot(
      documentId: number,
      sessionId?: string,
    ): Promise<CollaborationAutoSnapshotResponseDto> {
      const { data } = await this.client.post<CollaborationAutoSnapshotResponseDto>(
        `/collaboration/documents/${documentId}/auto-snapshot`,
        null,
        {
          params: { session_id: sessionId },
        },
      )
      return mapCollaborationAutoSnapshotResponseDto(data)
    }
  }

