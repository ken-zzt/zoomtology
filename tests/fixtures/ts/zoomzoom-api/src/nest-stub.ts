export function Injectable(): ClassDecorator { return () => {} }
export function Controller(_p?: string): ClassDecorator { return () => {} }
export function Get(_p?: string): MethodDecorator { return () => {} }
export function Patch(_p?: string): MethodDecorator { return () => {} }
export function Post(_p?: string): MethodDecorator { return () => {} }
export function Param(_p?: string): ParameterDecorator { return () => {} }
export function InjectRepository(_e: any): ParameterDecorator { return () => {} }
export function CommandHandler(_c: any): ClassDecorator { return () => {} }
export class CommandBus { execute(_c: any): Promise<any> { return null } }
export interface ICommandHandler<T> { execute(c: T): Promise<any> }
