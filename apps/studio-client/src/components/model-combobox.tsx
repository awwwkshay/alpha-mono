import { Check, ChevronsUpDown } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";

type ModelComboboxProps = {
  name: string;
  models: Array<string>;
  value: string;
  onChange: (value: string) => void;
};

function ModelCombobox({ name, models, value, onChange }: ModelComboboxProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");

  return (
    <div className="grid w-full min-w-0 gap-2">
      <input name={name} type="hidden" value={value} />
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            type="button"
            variant="outline"
            role="combobox"
            aria-expanded={open}
            className="w-full min-w-0 justify-between"
          >
            <span className="block min-w-0 flex-1 truncate text-left">
              {value || "Select model"}
            </span>
            <ChevronsUpDown className="size-4 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent align="start" className="w-96 max-w-[calc(100vw-2rem)]">
          <Command>
            <CommandInput
              placeholder="Search LiteLLM models"
              value={search}
              onValueChange={setSearch}
            />
            <CommandList>
              <CommandEmpty>
                <div className="grid gap-2 px-3 text-left">
                  <span>No model found.</span>
                  <Button
                    type="button"
                    variant="outline"
                    disabled={!search.trim()}
                    onClick={() => {
                      onChange(search.trim());
                      setOpen(false);
                    }}
                  >
                    Use “{search.trim() || "custom model"}”
                  </Button>
                </div>
              </CommandEmpty>
              <CommandGroup>
                {models.map((model) => (
                  <CommandItem
                    key={model}
                    value={model}
                    onSelect={(selected) => {
                      onChange(selected);
                      setOpen(false);
                    }}
                  >
                    <Check
                      className={cn("size-4", value === model ? "opacity-100" : "opacity-0")}
                    />
                    <span className="block min-w-0 flex-1 truncate">{model}</span>
                  </CommandItem>
                ))}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
    </div>
  );
}

export { ModelCombobox };
