import '@umijs/max';

/** Runtime request is provided by Umi's request plugin at build time. */
declare module '@umijs/max' {
  export function request<T = unknown>(
    url: string,
    options?: Record<string, unknown>,
  ): Promise<T>;
}
