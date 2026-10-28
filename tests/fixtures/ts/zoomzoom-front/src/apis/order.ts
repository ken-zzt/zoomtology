import fetchClient from '../helpers/fetch-client'
import { ApiMethodType, InstanceType } from '../types/helper'
export const fetchOrder = async function (id: number) {
  return fetchClient.get(InstanceType.Back, `zoomzoom/order/${id}`)
}
export const confirmOrder = async (id: number) =>
  fetchClient.request(InstanceType.Back, ApiMethodType.PATCH, `zoomzoom/order/${id}/confirmed`, {})
