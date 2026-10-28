import { Column, Entity, ManyToOne, OneToMany, PrimaryGeneratedColumn } from 'typeorm'
import { OrderProductEntity } from './order-product.entity'

@Entity({ name: 'zoom_order' })
export class OrderEntity {
  @PrimaryGeneratedColumn({ name: 'order_id' }) id: number
  @Column() orderStatusId: number
  @Column({ name: 'date_modified' }) dateModified: Date
  @OneToMany(() => OrderProductEntity, (p) => p.order) products: OrderProductEntity[]
}
