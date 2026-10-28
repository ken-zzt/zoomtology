import { Injectable } from '@nestjs/common'
import { CommandBus } from '@nestjs/cqrs'
import { OrderRepository } from './order.repository'
import { SQSOrderServiceKey } from '../constants/sqs-consumer'

export class ConfirmOrderCommand { constructor(readonly id: number) {} }

@Injectable()
export class OrderService {
  constructor(private readonly repo: OrderRepository, private readonly commandBus: CommandBus) {}

  async confirm(id: number) {
    await this.repo.confirm(id)
    this.notify(id)
    await this.commandBus.execute(new ConfirmOrderCommand(id))
    return this.send({ key: SQSOrderServiceKey.ConfirmOrder, payload: { orderId: id } })
  }
  private notify(id: number) { return id }
  private send(msg: any) { return msg }
}
