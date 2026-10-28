import { Column, Entity, ManyToOne, PrimaryGeneratedColumn } from 'typeorm'
import { OrderEntity } from './order.entity'

@Entity('zoom_order_product')
export class OrderProductEntity {
  @PrimaryGeneratedColumn() id: number
  @Column() orderId: number
  @ManyToOne(() => OrderEntity, (o) => o.products) order: OrderEntity
}
