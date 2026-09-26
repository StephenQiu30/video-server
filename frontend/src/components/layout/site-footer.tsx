import { cn } from 'cn';
import Link from 'next/link';
import { QuickParseDialog } from '@/components/intake/quick-parse-dialog';
import {
  NavigationMenu,
  NavigationMenuItem,
  NavigationMenuLink,
  NavigationMenuList,
} from '@/components/ui/navigation-menu';
import { siteConfig } from '@/lib/site';

export function SiteFooter({ className }: { className?: string }) {
  return (
    <footer className={cn('shrink-0 bg-card', className)}>
      <div className="content-shell flex min-h-16 flex-col justify-between gap-3 py-5 text-sm text-muted-foreground sm:flex-row sm:items-center">
        <div className="flex items-center gap-4">
          <Link className="focus-ring font-medium text-foreground" href="/">
            帧取 · FrameFetch
          </Link>
          <span>MIT 开源 · 请仅处理已获授权内容</span>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <QuickParseDialog />
          <NavigationMenu
            aria-label="项目链接"
            className="max-w-none flex-none"
            viewport={false}
          >
            <NavigationMenuList className="flex-wrap gap-4">
              <FooterLink href="/guide/">使用指南</FooterLink>
              <FooterLink href="/self-hosting/">自托管部署</FooterLink>
              <FooterLink href="/about/">关于</FooterLink>
              <FooterLink href={siteConfig.repositoryUrl}>GitHub</FooterLink>
              <FooterLink href={`${siteConfig.repositoryUrl}/tree/main/docs`}>
                文档
              </FooterLink>
              <FooterLink href={siteConfig.licenseUrl}>MIT License</FooterLink>
            </NavigationMenuList>
          </NavigationMenu>
        </div>
      </div>
    </footer>
  );
}

function FooterLink({ children, href }: { children: string; href: string }) {
  return (
    <NavigationMenuItem>
      <NavigationMenuLink asChild className="focus-ring">
        <Link href={href}>{children}</Link>
      </NavigationMenuLink>
    </NavigationMenuItem>
  );
}

export default SiteFooter;
