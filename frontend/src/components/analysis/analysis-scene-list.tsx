import { Button } from '@/components/ui/button';
import { Item, ItemGroup } from '@/components/ui/item';
import type { VideoAnalysisResult } from '@/types/video';
import { formatMilliseconds } from '@/utils/format';

export default function AnalysisSceneList({
  onSelectTime,
  scenes,
}: {
  onSelectTime?: (milliseconds: number) => void;
  scenes: VideoAnalysisResult['scenes'];
}) {
  return (
    <ItemGroup asChild className="hairline gap-0 border-y">
      <ol>
        {scenes.map((scene) => (
          <Item
            asChild
            className="hairline grid gap-4 rounded-none border-0 border-b px-0 py-6 last:border-b-0 sm:grid-cols-[72px_minmax(0,1fr)]"
            key={scene.id}
          >
            <li>
              <Button
                className="mt-2 h-11 w-fit px-0 text-xs text-muted-foreground tabular-nums"
                disabled={!onSelectTime}
                onClick={() => onSelectTime?.(scene.start_ms)}
                type="button"
                variant="link"
              >
                {formatMilliseconds(scene.start_ms)}
              </Button>
              <div>
                <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
                  <strong className="font-medium">
                    场景 {scene.index} · {scene.title}
                  </strong>
                  <span className="text-xs text-muted-foreground">
                    {scene.location}
                  </span>
                </div>
                <p className="mt-2 leading-7 text-muted-foreground">
                  {scene.description}
                </p>
                <p className="mt-3 text-sm">{scene.narrative_function}</p>
                <p className="mt-3 text-xs text-muted-foreground">
                  视觉规则：{scene.visual_rules.join(' · ')}
                </p>
                {scene.continuity_risks.length ? (
                  <p className="mt-2 text-xs text-muted-foreground">
                    连续性风险：{scene.continuity_risks.join(' · ')}
                  </p>
                ) : null}
              </div>
            </li>
          </Item>
        ))}
      </ol>
    </ItemGroup>
  );
}
