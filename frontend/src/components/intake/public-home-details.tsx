import { CheckCircleIcon } from '@phosphor-icons/react/dist/ssr';
import { cn } from 'cn';

import {
  Item,
  ItemContent,
  ItemDescription,
  ItemMedia,
  ItemTitle,
} from '@/components/ui/item';

type Capability = readonly [
  eyebrow: string,
  title: string,
  description: string,
];
type WorkflowStep = readonly [title: string, description: string];

export function PublicHomeCapabilities({
  items,
}: {
  items: readonly Capability[];
}) {
  return (
    <ul className={cn('mt-12 grid gap-10 md:grid-cols-3 md:gap-12')}>
      {items.map(([eyebrow, title, description]) => (
        <Item asChild className="block rounded-none p-0" key={title}>
          <li>
            <ItemContent className="gap-0">
              <ItemDescription className="font-mono text-xs leading-normal">
                {eyebrow}
              </ItemDescription>
              <h3 className={cn('mt-5 text-xl')}>{title}</h3>
              <ItemDescription className="mt-3 line-clamp-none max-w-md text-base leading-7">
                {description}
              </ItemDescription>
            </ItemContent>
          </li>
        </Item>
      ))}
    </ul>
  );
}

export function PublicHomeSafeguards({ items }: { items: readonly string[] }) {
  return (
    <ul className={cn('gap-5 self-end')}>
      {items.map((item) => (
        <Item
          asChild
          className="flex-nowrap items-start gap-3 rounded-none p-0"
          key={item}
        >
          <li>
            <ItemMedia className="mb-0">
              <CheckCircleIcon
                aria-hidden
                className="mt-1 size-5 shrink-0 text-success"
                weight="fill"
              />
            </ItemMedia>
            <ItemDescription className="line-clamp-none text-base leading-7 text-foreground">
              {item}
            </ItemDescription>
          </li>
        </Item>
      ))}
    </ul>
  );
}

export function PublicHomeWorkflow({
  items,
}: {
  items: readonly WorkflowStep[];
}) {
  return (
    <ol className={cn('mt-7 gap-6')}>
      {items.map(([title, description], index) => (
        <Item
          asChild
          className="grid grid-cols-[2rem_1fr] gap-4 rounded-none p-0"
          key={title}
        >
          <li>
            <ItemMedia className="mb-0 font-mono text-xs text-muted-foreground">
              {String(index + 1).padStart(2, '0')}
            </ItemMedia>
            <ItemContent>
              <ItemTitle className="text-base">{title}</ItemTitle>
              <ItemDescription className="line-clamp-none text-base leading-6">
                {description}
              </ItemDescription>
            </ItemContent>
          </li>
        </Item>
      ))}
    </ol>
  );
}
