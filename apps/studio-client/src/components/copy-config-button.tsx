import { Check, Copy } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { type YamlValue, toYaml } from "@/lib/yaml";

type CopyConfigButtonProps = {
  config: YamlValue;
};

function CopyConfigButton({ config }: CopyConfigButtonProps) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    await navigator.clipboard.writeText(toYaml(config));
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  }

  return (
    <Button
      variant="outline"
      size="sm"
      onClick={() => void handleCopy()}
      aria-label="Copy YAML configuration"
    >
      {copied ? <Check className="size-4" /> : <Copy className="size-4" />}
      {copied ? "Copied" : "Copy config"}
    </Button>
  );
}

export { CopyConfigButton };
