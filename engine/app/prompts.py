"""Prompt wording lives in the repo's prompts/ directory so non-developers can edit it.

Files are read on every call, so edits apply to the next request without a restart.
"""

import re

from app.config import ConfigError, settings

_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_PLACEHOLDER = re.compile(r"\{\{\s*(\w+)\s*\}\}")


class PromptError(ConfigError):
    """A prompt file is missing or has a wrong or missing placeholder; the message says how to fix it."""


def render(name: str, required: tuple[str, ...] = (), **values: str) -> str:
    """Reads prompts/<name>.md, drops <!-- comments --> and fills in {{placeholders}}.

    `required` placeholders carry safety rules (e.g. the output format), so an edit cannot drop them.
    """
    path = settings.prompts_dir / f"{name}.md"
    if not path.is_file():
        raise PromptError(f"Prompt file {path} is missing. Restore it from git: git checkout -- prompts/{name}.md")
    text = _COMMENT.sub("", path.read_text()).strip()

    def fill(match: re.Match) -> str:
        key = match.group(1)
        if key not in values:
            raise PromptError(
                f"{path} uses {{{{{key}}}}}, which the engine does not fill in. "
                f"Available: {', '.join('{{' + k + '}}' for k in values) or 'none'}."
            )
        return values[key]

    if missing := [key for key in required if key not in {m.group(1) for m in _PLACEHOLDER.finditer(text)}]:
        raise PromptError(
            f"{path} must keep {', '.join('{{' + k + '}}' for k in missing)}. Put it back where it was "
            f"(see git diff prompts/{name}.md)."
        )
    return _PLACEHOLDER.sub(fill, text)
