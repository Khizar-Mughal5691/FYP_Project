import { Button, PageHeader } from "../components/ui";

export default function NotFound() {
  return (
    <div className="flex flex-col items-start gap-6 py-12">
      <PageHeader eyebrow="404" title="Off the pitch" description="There is no page at this address." />
      <Button to="/">Back to the home page</Button>
    </div>
  );
}
