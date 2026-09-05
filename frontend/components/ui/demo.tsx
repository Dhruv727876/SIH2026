import DotBorderButton from "@/components/ui/dot-border-button";

export default function DotBorderButtonDemo() {
  return (
    <div className="flex h-[420px] w-full items-center justify-center overflow-hidden rounded-xl border border-border bg-[#111318]">
      <DotBorderButton mode="dark" className="h-full w-full" />
    </div>
  );
}
