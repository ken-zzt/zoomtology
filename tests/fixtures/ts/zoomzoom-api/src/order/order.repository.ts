import { InjectRepository } from '@nestjs/typeorm'
import { Repository, DataSource } from 'typeorm'
import { OrderEntity as Order } from '../entities/order.entity'
import { OrderProductEntity } from '../entities/order-product.entity'

export class OrderRepository {
  constructor(
    @InjectRepository(Order) private readonly orders: Repository<Order>,
    private readonly dataSource: DataSource,
  ) {}

  async findWithProducts(id: number) {
    return this.orders.createQueryBuilder('o').innerJoinAndSelect('o.products', 'p').where('o.order_id = :id', { id }).getOne()
  }

  async confirm(id: number) {
    await this.orders.update({ id }, { orderStatusId: 2 })
    const products = await this.dataSource.getRepository(OrderProductEntity).find({ where: { orderId: id } })
    await this.dataSource.manager.save(products)
    return this.dataSource.query('SELECT COUNT(*) AS n FROM zoom_order_product WHERE order_id = ?', [id])
  }
}
