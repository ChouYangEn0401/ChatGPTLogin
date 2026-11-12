import json
import subprocess

import pytest

from openai_login import NOT_FOUND, LoginError, argv, ask, parse_events

OK = "\n".join(json.dumps(e) for e in [
    {"type": "thread.started", "thread_id": "t1"},
    {"type": "turn.started"},
    {"type": "item.completed", "item": {"id": "i1", "type": "reasoning", "text": "..."}},
    {"type": "item.completed", "item": {"id": "i2", "type": "agent_message", "text": "好"}},
    {"type": "turn.completed", "usage": {"input_tokens": 10, "cached_input_tokens": 4, "output_tokens": 2,
                                         "reasoning_output_tokens": 1}},
])


class Done:
    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout, self.stderr, self.returncode = stdout, stderr, returncode


def test_parse_ok():
    r = parse_events("noise line\n" + OK)
    assert (r.text, r.thread_id) == ("好", "t1")
    assert r.usage == {"input": 10, "cached_input": 4, "output": 2, "reasoning": 1}


def test_last_agent_message_wins():
    extra = json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": "最後"}})
    assert parse_events(OK + "\n" + extra).text == "最後"


def test_failed_turn_raises_with_message():
    out = json.dumps({"type": "turn.failed", "error": {"message": "usage limit"}})
    with pytest.raises(LoginError, match="usage limit"):
        parse_events(out)


def test_no_text_raises():
    with pytest.raises(LoginError):
        parse_events(json.dumps({"type": "turn.started"}))


def test_argv_reads_prompt_from_stdin_and_is_read_only():
    a = argv("codex", model="gpt-x")
    assert a[:2] == ["codex", "exec"] and a[-1] == "-"
    assert a[a.index("--sandbox") + 1] == "read-only"
    assert "--ephemeral" in a and a[a.index("-m") + 1] == "gpt-x"
    assert "--ignore-user-config" not in a and "--ignore-user-config" in argv("codex", ignore_user_config=True)


def test_ask_passes_prompt_on_stdin_in_empty_cwd():
    seen = {}

    def runner(cmd, **kw):
        seen.update(cmd=cmd, **kw)
        return Done(OK)

    r = ask("你好", runner=runner, which=lambda: "codex")
    assert r.text == "好" and seen["input"] == "你好" and seen["cwd"]


def test_missing_binary():
    with pytest.raises(LoginError, match="codex"):
        ask("x", which=lambda: None)
    assert "codex login" in NOT_FOUND


def test_timeout_and_nonzero_exit():
    def slow(cmd, **kw):
        raise subprocess.TimeoutExpired(cmd, 1)

    with pytest.raises(LoginError, match="沒回"):
        ask("x", timeout=1, runner=slow, which=lambda: "codex")
    with pytest.raises(LoginError, match="結束碼 1"):
        ask("x", runner=lambda c, **k: Done("", "not logged in", 1), which=lambda: "codex")
