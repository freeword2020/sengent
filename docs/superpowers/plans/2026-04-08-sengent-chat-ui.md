# Sengent Chat UI Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a non-fullscreen `rich`-based shell around `sentieon_assist chat` so Sengent always starts with a guided welcome panel and each turn shows user input, a real event stream, and a clearer final-answer block.

**Architecture:** Keep the current chat business logic and query routing intact, but move terminal presentation into a dedicated rendering layer. Introduce a small event-mapping module so the CLI can emit real processing stages without pretending to have tool execution, and keep non-`chat` commands on plain text output.

**Tech Stack:** Python 3.11, `rich`, pytest, existing CLI/chat loop, existing local-Ollama streaming path

---

## Chunk 1: UI Foundation

### Task 1: Add the `rich` dependency and chat UI primitives

**Files:**
- Modify: `pyproject.toml`
- Create: `src/sentieon_assist/chat_ui.py`
- Create: `tests/test_chat_ui.py`

- [ ] **Step 1: Write the failing tests**

Add tests for:

- a welcome panel renderer that includes `Sengent`
- a user message renderer that labels the turn as `你`
- an answer renderer that labels the final block as `Sengent`

Use `rich.console.Console(record=True)` so the UI layer can be tested without a real terminal.

```python
from rich.console import Console

from sentieon_assist.chat_ui import ChatUI


def test_render_welcome_panel_contains_brand_and_examples():
    console = Console(record=True, width=100)
    ui = ChatUI(console=console)

    ui.render_welcome_panel()

    text = console.export_text()
    assert "Sengent" in text
    assert "我可以帮你做什么" in text
    assert "/quit" in text


def test_render_user_message_marks_user_role():
    console = Console(record=True, width=100)
    ui = ChatUI(console=console)

    ui.render_user_message("DNAscope 是做什么的")

    text = console.export_text()
    assert "你" in text
    assert "DNAscope 是做什么的" in text


def test_render_answer_marks_sengent_role():
    console = Console(record=True, width=100)
    ui = ChatUI(console=console)

    ui.render_answer("【模块介绍】\nDNAscope：用于 germline variant calling")

    text = console.export_text()
    assert "Sengent" in text
    assert "【模块介绍】" in text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_chat_ui.py -v`
Expected: FAIL with import errors because `rich` and `chat_ui.py` do not exist yet.

- [ ] **Step 3: Add the dependency and minimal rendering layer**

Update `pyproject.toml` to add `rich` as a runtime dependency.

Create `src/sentieon_assist/chat_ui.py` with:

- a `ChatUI` class that accepts a `Console`
- `render_welcome_panel()`
- `render_user_message(text)`
- `render_answer(text)`
- a small helper for a shared `Console` when no console is passed in

Keep the first implementation minimal and deterministic:

```python
from dataclasses import dataclass, field

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text


def build_console() -> Console:
    return Console()


@dataclass
class ChatUI:
    console: Console = field(default_factory=build_console)

    def render_welcome_panel(self) -> None:
        self.console.print(
            Panel.fit(
                "欢迎使用 Sengent\\n\\n"
                "示例提问：\\n"
                "- Sentieon 202503 license 报错\\n"
                "- install 失败，命令不可用\\n"
                "- DNAscope 是做什么的\\n\\n"
                "我可以帮你做什么：\\n"
                "- 许可证排障\\n"
                "- 安装排障\\n"
                "- 模块和参数查询\\n\\n"
                "常用命令：\\n"
                "- /quit\\n"
                "- /reset",
                title="Sengent",
            )
        )
        self.console.print(Rule())

    def render_user_message(self, text: str) -> None:
        self.console.print(f"你\\n{text}")

    def render_answer(self, text: str) -> None:
        self.console.print(Panel(text, title="Sengent"))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_chat_ui.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/sentieon_assist/chat_ui.py tests/test_chat_ui.py
git commit -m "feat: add Sengent chat UI primitives"
```

### Task 2: Add deterministic chat event mapping

**Files:**
- Create: `src/sentieon_assist/chat_events.py`
- Modify: `tests/test_chat_ui.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write the failing tests**

Add tests for:

- rendering an event stream block with ordered stage lines
- building event labels for a missing-info path
- building event labels for a reference-query path

```python
from sentieon_assist.chat_events import (
    event_check_missing_info,
    event_detect_issue_type,
    event_prepare_reference_answer,
)


def test_render_event_stream_prints_all_events():
    console = Console(record=True, width=100)
    ui = ChatUI(console=console)

    ui.render_events([
        "已识别问题类型：资料查询",
        "正在检索本地资料",
        "正在整理参考答案",
    ])

    text = console.export_text()
    assert "事件流" in text
    assert "已识别问题类型：资料查询" in text
    assert "正在整理参考答案" in text


def test_missing_info_event_text_is_deterministic():
    assert event_detect_issue_type("license") == "已识别问题类型：license"
    assert event_check_missing_info(["version"]) == "发现需要补充的信息：Sentieon 版本"


def test_reference_path_event_text_is_deterministic():
    assert event_prepare_reference_answer() == "正在整理参考答案"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_chat_ui.py tests/test_cli.py -k 'event' -v`
Expected: FAIL because `chat_events.py` and `render_events()` do not exist yet.

- [ ] **Step 3: Add the minimal event module and renderer**

Create `src/sentieon_assist/chat_events.py` with narrowly scoped helpers:

- `event_detect_issue_type(issue_type: str) -> str`
- `event_check_missing_info(missing_fields: list[str]) -> str`
- `event_search_sources() -> str`
- `event_prepare_reference_answer() -> str`
- `event_generate_reply() -> str`

Use existing field labels from `answering.py` where practical, or mirror them locally if importing them would cause circular dependencies.

Extend `ChatUI` with:

```python
from rich.panel import Panel


def render_events(self, events: list[str]) -> None:
    if not events:
        return
    body = "\\n".join(f"- {event}" for event in events)
    self.console.print(Panel(body, title="事件流"))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_chat_ui.py tests/test_cli.py -k 'event' -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/sentieon_assist/chat_events.py src/sentieon_assist/chat_ui.py tests/test_chat_ui.py tests/test_cli.py
git commit -m "feat: add Sengent chat event stream"
```

## Chunk 2: CLI Integration and Docs

### Task 3: Wire the chat loop to the new UI and preserve streaming behavior

**Files:**
- Modify: `src/sentieon_assist/cli.py`
- Modify: `tests/test_cli.py`
- Test: `tests/test_chat_ui.py`

- [ ] **Step 1: Write the failing tests**

Add or update tests that require:

- the welcome panel to print every time `chat` starts
- each turn to emit user message -> event stream -> final answer in order
- missing-info turns to emit a missing-info event before the answer
- `/reset` and `/quit` to remain unchanged
- the input prompt to use the `Sengent` brand

```python
def test_chat_loop_prints_welcome_panel_before_first_prompt():
    prompts = iter(["/quit"])
    outputs: list[str] = []

    code = main(
        ["chat"],
        input_fn=lambda _prompt: next(prompts),
        output_fn=outputs.append,
        api_probe=lambda base_url: {"ok": True, "model_available": True},
    )

    assert code == 0
    assert any("Sengent" in item for item in outputs)


def test_chat_loop_renders_user_events_and_answer_in_order(monkeypatch):
    prompts = iter(["DNAscope 是做什么的", "/quit"])
    outputs: list[str] = []

    monkeypatch.setattr("sentieon_assist.cli.run_query", lambda query, **kwargs: "【模块介绍】\\nDNAscope：...")

    code = main(
        ["chat"],
        input_fn=lambda _prompt: next(prompts),
        output_fn=outputs.append,
        api_probe=lambda base_url: {"ok": True, "model_available": True},
        model_generate=lambda prompt, **kwargs: "SHOULD_NOT_RUN",
    )

    assert code == 0
    joined = "\\n".join(outputs)
    assert joined.index("你") < joined.index("事件流")
    assert joined.index("事件流") < joined.index("Sengent")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cli.py tests/test_chat_ui.py -k 'chat_loop or welcome or Sengent' -v`
Expected: FAIL because the current chat loop still writes plain strings and the prompt still uses the old raw loop behavior.

- [ ] **Step 3: Refactor `cli.py` to use the UI layer**

Refactor `src/sentieon_assist/cli.py` so that:

- `chat_loop()` constructs one `ChatUI` instance at startup
- `chat_loop()` calls `render_welcome_panel()` before the first prompt
- the input prompt becomes `Sengent> `
- each turn renders the user message before running business logic
- the loop derives a short event list from the path taken:
  - always emit issue classification
  - emit missing-info check
  - emit source-search/reference-prep where relevant
  - emit model generation only when the final answer is actually model-generated
- stable structured answers keep bypassing model polish, as they do today
- final output goes through `ChatUI.render_answer()` or a dedicated streamed-answer method

Do not change:

- `run_query()` behavior
- doctor/sources/search modes
- reference-answer semantics

Minimal integration shape:

```python
ui = ChatUI()
ui.render_welcome_panel()

while True:
    query = input_fn("Sengent> ").strip()
    ...
    ui.render_user_message(query)
    events = build_chat_events(...)
    ui.render_events(events)
    rendered, streamed = render_chat_response(...)
    if not streamed:
        ui.render_answer(rendered)
```

- [ ] **Step 4: Run targeted tests to verify they pass**

Run: `pytest tests/test_cli.py tests/test_chat_ui.py -v`
Expected: PASS

- [ ] **Step 5: Run the full suite to verify no regression**

Run: `pytest -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/sentieon_assist/cli.py src/sentieon_assist/chat_ui.py src/sentieon_assist/chat_events.py tests/test_cli.py tests/test_chat_ui.py pyproject.toml
git commit -m "feat: add Sengent rich chat shell"
```

### Task 4: Update docs for the Sengent chat shell

**Files:**
- Modify: `README.md`
- Modify: `docs/project-context.md`

- [ ] **Step 1: Write the failing doc check**

Verify the current docs do not yet describe the new shell:

Run: `rg -n "Sengent|欢迎面板|事件流|rich" README.md docs/project-context.md`
Expected: no relevant matches for the new chat shell design

- [ ] **Step 2: Write the minimal documentation**

Update `README.md` to reflect:

- chat now launches with a `Sengent` welcome panel
- the terminal UI is still non-fullscreen
- turns are displayed as user message + event stream + final answer
- `rich` is now a runtime dependency

Update `docs/project-context.md` to reflect:

- new `chat_ui.py` responsibility
- new `chat_events.py` responsibility
- completed milestone for chat UX shell if implementation is done

- [ ] **Step 3: Run doc sanity checks**

Run: `rg -n "Sengent|欢迎面板|事件流|rich" README.md docs/project-context.md`
Expected: matches in both files

- [ ] **Step 4: Commit**

```bash
git add README.md docs/project-context.md
git commit -m "docs: describe Sengent chat shell"
```

Plan complete and saved to `docs/superpowers/plans/2026-04-08-sengent-chat-ui.md`. Ready to execute?
