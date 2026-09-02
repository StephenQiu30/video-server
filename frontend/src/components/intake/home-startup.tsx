export function HomeStartup() {
  return (
    <section
      aria-atomic="true"
      aria-live="polite"
      className="absolute inset-0 z-20 flex min-h-[60vh] items-center bg-background"
      data-home-boot
      data-slot="home-session-startup"
      role="status"
    >
      <div className="w-full max-w-md" data-home-boot-copy>
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-muted-foreground">
          FrameFetch / Session
        </p>
        <p className="mt-4 text-xl font-medium tracking-[-0.025em]">
          正在确认当前会话
        </p>
        <p className="mt-2 leading-6 text-muted-foreground">
          工作区准备完成后，只呈现与你登录状态匹配的页面。
        </p>
        <div aria-hidden className="mt-6 h-px w-full overflow-hidden bg-border">
          <span
            className="block h-full w-full origin-left bg-foreground"
            data-home-boot-line
          />
        </div>
      </div>
    </section>
  );
}
