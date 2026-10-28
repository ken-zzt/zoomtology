import { HttpMethod } from '../../net/http-client'
class AccessRule {
  constructor(readonly method: string, readonly source: string, readonly target: string, readonly auth: boolean, readonly login: boolean, readonly version = 0) {}
}
class AccessMiddleware {
  static readonly rules = new Array<AccessRule>(
    new AccessRule(HttpMethod.Patch, '^order/[0-9]+/confirmed$', null, true, false, 1),
    new AccessRule(HttpMethod.Get, '^order/', null, true, true, 0),
    new AccessRule(HttpMethod.Get, '^cart/me$', 'cart/me', false, true, 0),
  )
  static find(method, url) { return AccessMiddleware.rules.find((r) => r.method === method && new RegExp(r.source).test(url)) }
}
export class ZoomZoomService {}
