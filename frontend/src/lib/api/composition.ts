import type { ApiHttpClient, Constructor } from './httpClient'

export type ApiClientMixin = <TBase extends Constructor<ApiHttpClient>>(
  Base: TBase,
) => Constructor<any>

type UnionToIntersection<TUnion> = (
  TUnion extends unknown ? (value: TUnion) => void : never
) extends (value: infer TIntersection) => void
  ? TIntersection
  : never

type MixinMembers<TMixin extends ApiClientMixin> = TMixin extends <
  TBase extends Constructor<ApiHttpClient>,
>(
  Base: TBase,
) => Constructor<infer TInstance>
  ? Omit<TInstance, keyof ApiHttpClient>
  : never

export type ComposedApiClient<TMixins extends readonly ApiClientMixin[]> = ApiHttpClient &
  UnionToIntersection<MixinMembers<TMixins[number]>>

export function composeApiClient<TMixins extends readonly ApiClientMixin[]>(
  Base: Constructor<ApiHttpClient>,
  mixins: TMixins,
): Constructor<ComposedApiClient<TMixins>> {
  return mixins.reduce(
    (CurrentBase, applyMixin) => applyMixin(CurrentBase),
    Base,
  ) as Constructor<ComposedApiClient<TMixins>>
}
