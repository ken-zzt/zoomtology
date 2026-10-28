import { HttpClient } from 'src/helpers/http-client'
import { IService } from 'src/interfaces/service'
export class ConfirmOrderService implements IService {
  async execute(payload: any) {
    await HttpClient.Patch<any>(`${process.env.BACK_API_SERVER_URL}/zoomzoom/order/${payload.orderId}/confirmed`, {}, payload)
    await HttpClient.Get<any>(`${process.env.BACK_API_SERVER_URL}/zoomzoom/nothing/${payload.x ? `a` : ''}`, {})
  }
}
