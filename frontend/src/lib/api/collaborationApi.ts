import type { ApiHttpClient, Constructor } from './httpClient'

export const CollaborationApiMixin = <TBase extends Constructor<ApiHttpClient>>(Base: TBase) =>
  class extends Base {
    constructor(...args: any[]) {
      super(...args)
    }

    async getCollabToken(documentId: number): Promise<{
      token: string
      document_id: number
      permissions: string[]
      websocket_url: string
      expires_in: number
    }> {
      const { data } = await this.client.post('/auth/collab-token', { document_id: documentId })
      return data
    }

    async getCollaborationStatus(documentId: number): Promise<{
      document_id: number
      active_collaborators: Array<{
        user_id: number
        username: string
        color: string
        is_editing: boolean
      }>
      is_collaborative_mode: boolean
      has_unsaved_changes: boolean
    }> {
      const { data } = await this.client.get(`/collaboration/documents/${documentId}/status`)
      return data
    }

    async startCollaborationSession(documentId: number): Promise<{
      session_id: string
      document_id: number
      started_at: string
    }> {
      const { data } = await this.client.post('/collaboration/sessions/start', {
        document_id: documentId,
      })
      return data
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
    ): Promise<{
      document_id: number
      activities: Array<{
        id: number
        document_id: number
        user_id: number
        username: string
        activity_type: string
        details: Record<string, unknown> | null
        created_at: string
      }>
      total: number
      has_more: boolean
    }> {
      const { data } = await this.client.get(`/collaboration/documents/${documentId}/activity`, {
        params: { limit, offset },
      })
      return data
    }

    async getActiveSessions(documentId: number): Promise<{
      document_id: number
      sessions: Array<{
        session_id: string
        user_id: number
        username: string
        started_at: string
        last_activity_at: string
        edits_count: number
      }>
      count: number
    }> {
      const { data } = await this.client.get(`/collaboration/documents/${documentId}/sessions`)
      return data
    }

    async createSnapshot(
      documentId: number,
      options?: { name?: string; description?: string; session_id?: string },
    ): Promise<{
      id: number
      document_id: number
      snapshot_type: string
      name: string | null
      description: string | null
      state_size: number
      created_by: number | null
      created_by_username: string | null
      session_id: string | null
      is_pinned: boolean
      expires_at: string | null
      created_at: string
    }> {
      const { data } = await this.client.post(
        `/collaboration/documents/${documentId}/snapshots`,
        options || {},
      )
      return data
    }

    async listSnapshots(
      documentId: number,
      options?: { limit?: number; offset?: number; include_expired?: boolean },
    ): Promise<{
      document_id: number
      snapshots: Array<{
        id: number
        document_id: number
        snapshot_type: string
        name: string | null
        description: string | null
        state_size: number
        created_by: number | null
        created_by_username: string | null
        session_id: string | null
        is_pinned: boolean
        expires_at: string | null
        created_at: string
      }>
      total: number
      has_more: boolean
    }> {
      const { data } = await this.client.get(`/collaboration/documents/${documentId}/snapshots`, {
        params: options,
      })
      return data
    }

    async getSnapshot(documentId: number, snapshotId: number): Promise<{
      id: number
      document_id: number
      snapshot_type: string
      name: string | null
      description: string | null
      state_size: number
      created_by: number | null
      created_by_username: string | null
      session_id: string | null
      is_pinned: boolean
      expires_at: string | null
      created_at: string
    }> {
      const { data } = await this.client.get(
        `/collaboration/documents/${documentId}/snapshots/${snapshotId}`,
      )
      return data
    }

    async restoreSnapshot(
      documentId: number,
      snapshotId: number,
      sessionId?: string,
    ): Promise<{
      message: string
      snapshot_id: number
      snapshot_name: string
      document_id: number
    }> {
      const { data } = await this.client.post(
        `/collaboration/documents/${documentId}/snapshots/${snapshotId}/restore`,
        { session_id: sessionId },
      )
      return data
    }

    async updateSnapshot(
      documentId: number,
      snapshotId: number,
      updates: { name?: string; description?: string; is_pinned?: boolean },
    ): Promise<{
      id: number
      document_id: number
      snapshot_type: string
      name: string | null
      description: string | null
      state_size: number
      created_by: number | null
      created_by_username: string | null
      session_id: string | null
      is_pinned: boolean
      expires_at: string | null
      created_at: string
    }> {
      const { data } = await this.client.patch(
        `/collaboration/documents/${documentId}/snapshots/${snapshotId}`,
        updates,
      )
      return data
    }

    async deleteSnapshot(documentId: number, snapshotId: number): Promise<void> {
      await this.client.delete(`/collaboration/documents/${documentId}/snapshots/${snapshotId}`)
    }

    async createAutoSnapshot(
      documentId: number,
      sessionId?: string,
    ): Promise<{
      created: boolean
      reason?: string
      snapshot_id?: number
      snapshot_name?: string
    }> {
      const { data } = await this.client.post(
        `/collaboration/documents/${documentId}/auto-snapshot`,
        null,
        {
          params: { session_id: sessionId },
        },
      )
      return data
    }
  }

