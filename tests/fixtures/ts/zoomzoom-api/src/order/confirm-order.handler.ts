import { CommandHandler, ICommandHandler } from '@nestjs/cqrs'
import { ConfirmOrderCommand } from './order.service'
import { OrderRepository } from './order.repository'

@CommandHandler(ConfirmOrderCommand)
export class ConfirmOrderHandler implements ICommandHandler<ConfirmOrderCommand> {
  constructor(private readonly repo: OrderRepository) {}
  async execute(cmd: ConfirmOrderCommand) { return this.repo.findWithProducts(cmd.id) }
}
