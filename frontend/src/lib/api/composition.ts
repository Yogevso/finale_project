import type { ApiClientBase, Constructor } from './httpClient'

export type ApiClientMixin = <TBase extends Constructor<ApiClientBase>>(
  Base: TBase,
) => Constructor<InstanceType<TBase>>

type UnionToIntersection<TUnion> = (
  TUnion extends unknown ? (value: TUnion) => void : never
) extends (value: infer TIntersection) => void
  ? TIntersection
  : never

type MixinMembers<TMixin> = TMixin extends <
  TBase extends Constructor<ApiClientBase>,
>(
  Base: TBase,
) => Constructor<infer TInstance>
  ? Omit<TInstance, keyof ApiClientBase>
  : never

export type ComposedApiClient<TMixins extends readonly unknown[]> = ApiClientBase &
  UnionToIntersection<MixinMembers<TMixins[number]>>

export function composeApiClient<TMixins extends readonly unknown[]>(
  Base: Constructor<ApiClientBase>,
  mixins: TMixins,
): Constructor<ComposedApiClient<TMixins>> {
  let CurrentBase: Constructor<object> = Base
  for (const applyMixin of mixins) {
    CurrentBase = (applyMixin as ApiClientMixin)(CurrentBase as Constructor<ApiClientBase>)
  }
  return CurrentBase as Constructor<ComposedApiClient<TMixins>>
}
