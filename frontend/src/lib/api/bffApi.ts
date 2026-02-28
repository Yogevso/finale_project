import type { DocumentDetailPageBundle } from '@/types'
import {
  type DocumentDetailPageBundleDto,
  mapDocumentDetailPageBundleDto,
} from './dto'
import type { ApiHttpClient, Constructor } from './httpClient'

export const BffApiMixin = <TBase extends Constructor<ApiHttpClient>>(Base: TBase) =>
  class extends Base {
    constructor(...args: any[]) {
      super(...args)
    }

    async getDocumentDetailPageBundle(documentId: number): Promise<DocumentDetailPageBundle> {
      const { data } = await this.client.get<DocumentDetailPageBundleDto>(
        `/bff/documents/${documentId}/detail-page`,
      )
      return mapDocumentDetailPageBundleDto(data)
    }
  }

