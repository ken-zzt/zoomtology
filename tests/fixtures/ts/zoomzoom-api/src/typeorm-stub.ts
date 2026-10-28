// 테스트용 typeorm 최소 타입 — 타입 해석(manager.save 인자 타입)에만 쓴다
export function Entity(_a?: any): ClassDecorator { return () => {} }
export function Column(_a?: any): PropertyDecorator { return () => {} }
export function PrimaryGeneratedColumn(_a?: any): PropertyDecorator { return () => {} }
export function ManyToOne(_a?: any, _b?: any): PropertyDecorator { return () => {} }
export function OneToMany(_a?: any, _b?: any): PropertyDecorator { return () => {} }
export class Repository<T> {
  createQueryBuilder(_alias?: string): any { return null }
  update(_c: any, _v: any): Promise<any> { return null }
  find(_o?: any): Promise<T[]> { return null }
}
export class EntityManager {
  save<T>(e: T): Promise<T> { return null }
}
export class DataSource {
  manager: EntityManager
  getRepository<T>(_e: new () => T): Repository<T> { return null }
  query(_sql: string, _p?: any[]): Promise<any> { return null }
}
