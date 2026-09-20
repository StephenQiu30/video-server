export function RouteLoading({ label = '正在加载页面' }: { label?: string }) {
  return (
    <div
      aria-label={label}
      className="flex min-h-[60vh] items-center justify-center gap-3 text-sm text-muted-foreground"
      data-slot="route-loading"
      role="status"
    >
      <span
        aria-hidden
        className="size-5 animate-spin rounded-full border-2 border-muted border-t-foreground motion-reduce:animate-none"
      />
      <span>{label}</span>
    </div>
  );
}
