import { Controller, Post } from '@nestjs/common'
@Controller('task/order')
export class OrderTaskController {
  @Post('expire')
  async expire() { return 1 }
}
