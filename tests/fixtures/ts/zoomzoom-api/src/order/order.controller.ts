import { Controller, Get, Param, Patch } from '@nestjs/common'
import { OrderService } from './order.service'

@Controller('order')
export class OrderController {
  constructor(private readonly service: OrderService) {}
  @Patch(':id/confirmed')
  async confirmed(@Param('id') id: number) { return this.service.confirm(id) }
  @Get('/:id')
  async get(@Param('id') id: number) { return id }
}
