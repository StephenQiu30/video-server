import { absoluteUrl } from '@/lib/site';

export function JsonLd({ data }: { data: object }) {
  return (
    <script type="application/ld+json">
      {JSON.stringify(data).replace(/</g, '\\u003c')}
    </script>
  );
}

export function breadcrumbList(items: { name: string; path: string }[]) {
  return {
    '@type': 'BreadcrumbList',
    itemListElement: items.map(({ name, path }, index) => ({
      '@type': 'ListItem',
      position: index + 1,
      name,
      item: absoluteUrl(path),
    })),
  };
}
