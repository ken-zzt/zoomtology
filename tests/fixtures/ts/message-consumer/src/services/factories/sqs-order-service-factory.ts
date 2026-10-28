import { SQSOrderServiceKey } from 'src/constants/sqs-order-service-key'
import { IService } from 'src/interfaces/service'
import { ConfirmOrderService } from '../sqs/confirm-order'
export class SQSOrderServiceFactory {
  static getInstance(): Map<SQSOrderServiceKey, IService> {
    const map = new Map<SQSOrderServiceKey, IService>()
    map.set(SQSOrderServiceKey.ConfirmOrder, new ConfirmOrderService())
    return map
  }
}
