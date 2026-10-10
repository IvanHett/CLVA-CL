"""Response generator: turns a resolved intent into answer text (KB / module / fallback)."""
from . import config
from .data_loader import Dataset, Module
from .pipeline import Resolution


class ResponseGenerator:
    def __init__(self, dataset: Dataset):
        self._dataset = dataset

    def generate(self, resolution: Resolution) -> str:
        if not resolution.matched:
            return config.FALLBACK_RESPONSE
        if resolution.intent == "module_info":
            return self._module_info(resolution.module)
        if resolution.intent == "module_list":
            return self._module_list()
        return self._dataset.answers.get(resolution.intent) or config.FALLBACK_RESPONSE

    def _module_info(self, module: Module | None) -> str:
        if module is None:
            codes = ", ".join(m.module_id for m in self._dataset.modules)
            return (
                "Which module would you like to know about? Give me its code or name, "
                f"for example 'Tell me about {self._dataset.modules[0].module_id}'. "
                f"Available modules: {codes}."
            )
        assessment = module.assessment or "see the module guide on Canvas"
        return (
            f"{module.module_id} {module.module_name}\n"
            f"Year {module.year}, {module.credits} credits, {module.module_type.lower()} module\n"
            f"{module.description}\n"
            f"Assessment: {assessment}"
        )

    def _module_list(self) -> str:
        lines = ["These are the modules on the course:"]
        for year in sorted({m.year for m in self._dataset.modules}):
            lines.append(f"\nYear {year}")
            lines.extend(
                f"  {m.module_id}  {m.module_name}" + (" (optional)" if m.module_type == "Optional" else "")
                for m in self._dataset.modules if m.year == year
            )
        lines.append("\nAsk me about any module by its code or name for more detail.")
        return "\n".join(lines)
