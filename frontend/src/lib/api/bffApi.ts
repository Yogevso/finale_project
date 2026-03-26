import type { DocumentDetailPageBundle } from '@/types'
import {
  type DocumentDetailPageBundleDto,
  mapDocumentDetailPageBundleDto,
} from './dto'
import type { ApiClientBase, Constructor } from './httpClient'

export const BffApiMixin = <TBase extends Constructor<ApiClientBase>>(Base: TBase) =>
  class extends Base {
    async getDocumentDetailPageBundle(documentId: number): Promise<DocumentDetailPageBundle> {
      const { data } = await this.client.get<DocumentDetailPageBundleDto>(
        `/bff/documents/${documentId}/detail-page`,
      )
      return mapDocumentDetailPageBundleDto(data)
    }
  }
