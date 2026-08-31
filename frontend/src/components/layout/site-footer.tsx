import Link from 'next/link';
import {
  NavigationMenu,
  NavigationMenuItem,
  NavigationMenuLink,
  NavigationMenuList,
} from '@/components/ui/navigation-menu';
import { siteConfig } from '@/lib/site';
import { cn } from '@/lib/utils';

export function SiteFooter({ className }: { className?: string }) {
  return (
    <footer className={cn('shrink-0 bg-background', className)}>
      <div className="content-shell flex min-h-16 flex-col justify-between gap-3 py-5 text-xs text-muted-foreground sm:flex-row sm:items-center">
        <div className="flex items-center gap-4">
          <Link className="focus-ring font-medium text-foreground" href="/">
            帧取 · FrameFetch
          </Link>
          <span>MIT 开源 · 请仅处理已获授权内容</span>
        </div>
        <NavigationMenu
          aria-label="项目链接"
          className="max-w-none flex-none"
          viewport={false}
        >
          <NavigationMenuList className="gap-4">
            <FooterLink href={siteConfig.repositoryUrl}>GitHub</FooterLink>
            <FooterLink href={`${siteConfig.repositoryUrl}/tree/main/docs`}>
              文档
            </FooterLink>
            <FooterLink href={siteConfig.licenseUrl}>MIT License</FooterLink>
          </NavigationMenuList>
        </NavigationMenu>
      </div>
    </footer>
  );
}

function FooterLink({ children, href }: { children: string; href: string }) {
  return (
    <NavigationMenuItem>
      <NavigationMenuLink
        asChild
        className="focus-ring rounded-md p-0 text-xs text-muted-foreground hover:bg-transparent hover:text-foreground focus:bg-transparent"
      >
        <Link href={href}>{children}</Link>
      </NavigationMenuLink>
    </NavigationMenuItem>
  );
}

export default SiteFooter;
