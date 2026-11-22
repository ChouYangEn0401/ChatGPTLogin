"""統一呼叫介面（三個訂閱登入套件共用的名字）：訊息清單、Result、錯誤分類。全部用假的 runner，不叫真的 codex。"""

import json
import os
import subprocess

import pytest

import chatgpt_login as cl
from chatgpt_login import (CAPABILITIES, INTERFACE_VERSION, AuthError, CallTimeoutError, LoginError,
                           NotInstalledError, Reply, Result, UsageLimitError, ask, flatten_messages, parse_events)

OK = "\n".join(json.dumps(e) for e in [
    {"type": "thread.started", "thread_id": "t1"},
    {"type": "item.completed", "item": {"id": "i2", "type": "agent_message", "text": "好"}},
    {"type": "turn.completed", "usage": {"input_tokens": 10, "cached_input_tokens": 4, "output_tokens": 2}},
])


class Done:
    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout, self.stderr, self.returncode = stdout, stderr, returncode


def capture(out=OK):
    seen = {}

    def runner(cmd, **kw):
        seen.update(cmd=cmd, **kw)
        return Done(out)

    return seen, runner


def failed(message):
    return json.dumps({"type": "turn.failed", "error": {"message": message}})


def test_names_and_hierarchy():
    assert Result is Reply and INTERFACE_VERSION == "1"
    for cls in (UsageLimitError, AuthError, NotInstalledError, CallTimeoutError):
        assert issubclass(cls, LoginError)
    assert [c.kind for c in (LoginError, UsageLimitError, AuthError, NotInstalledError, CallTimeoutError)] == \
        ["unknown", "quota_exhausted", "auth_invalid", "not_installed", "timeout"]
    for name in ("INTERFACE_VERSION", "CAPABILITIES", "Result", "UsageLimitError", "AuthError",
                 "NotInstalledError", "CallTimeoutError", "flatten_messages"):
        assert name in cl.__all__


def test_capabilities_are_honest():
    assert CAPABILITIES["tools"] is False and CAPABILITIES["usage"] is True and CAPABILITIES["stream"] is False
    assert CAPABILITIES["agent_sandbox"] == "read-only" and CAPABILITIES["verified_with_real_cli"] is False


def test_result_shape():
    seen, runner = capture()
    r = ask("hi", model="gpt-x", runner=runner, which=lambda: "codex")
    assert (r.text, r.model, r.thread_id) == ("好", "gpt-x", "t1")
    assert r.usage == {"input": 10, "cached_input": 4, "output": 2, "reasoning": 0}
    assert isinstance(r.raw, list) and r.raw[0]["type"] == "thread.started"
    assert ask("hi", runner=runner, which=lambda: "codex").model == ""
    assert "-m" not in seen["cmd"]


def test_messages_are_flattened_and_system_prepended_on_stdin():
    seen, runner = capture()
    ask([{"role": "system", "content": "be brief"}, {"role": "user", "content": "q1"},
         {"role": "assistant", "content": "a1"}, {"role": "user", "content": "q2"}],
        runner=runner, which=lambda: "codex")
    sent = seen["input"]
    assert sent.startswith("[Instructions]\nbe brief\n\n[Request]\n")
    assert sent.endswith("### User\nq1\n\n### Assistant\na1\n\n### User\nq2")
    assert seen["cmd"][-1] == "-"


def test_single_message_is_sent_as_is():
    seen, runner = capture()
    ask([{"role": "user", "content": "只有一句"}], runner=runner, which=lambda: "codex")
    assert seen["input"] == "只有一句"


def test_flatten_rejects_tools_images_and_bad_order():
    for msgs in ([{"role": "tool", "content": "x"}, {"role": "user", "content": "y"}],
                 [{"role": "user", "content": [{"type": "input_image"}]}],
                 [{"role": "user", "content": "a"}, {"role": "assistant", "content": "b"}],
                 []):
        with pytest.raises(ValueError):
            flatten_messages(msgs)


@pytest.mark.parametrize("message,cls", [
    ("You've hit your usage limit. Try again in 2 hours 5 minutes.", UsageLimitError),
    ("exceeded retry limit, last status: 429 Too Many Requests", UsageLimitError),
    ("unexpected status 401 Unauthorized", AuthError),
    ("Your access token could not be refreshed. Please log in again.", AuthError),
    ("model overloaded", LoginError),
])
def test_turn_failed_is_classified(message, cls):
    with pytest.raises(LoginError) as info:
        parse_events(failed(message))
    assert type(info.value) is cls
    assert message.split(".")[0] in str(info.value)


def test_retry_after_from_relative_time():
    with pytest.raises(UsageLimitError) as info:
        parse_events(failed("You've hit your usage limit. Try again in 2 hours 5 minutes."))
    assert info.value.resets == "2 hours 5 minutes" and info.value.retry_after == 7500
    with pytest.raises(UsageLimitError) as info:
        parse_events(failed("usage limit reached; try again at 5:03 PM"))
    assert info.value.resets.startswith("5:03 PM") and info.value.retry_after is None


def test_classified_failure_survives_nonzero_exit():
    with pytest.raises(UsageLimitError):
        ask("x", runner=lambda c, **k: Done(failed("usage limit"), "", 1), which=lambda: "codex")


def test_nonzero_exit_stderr_is_classified():
    with pytest.raises(AuthError) as info:
        ask("x", runner=lambda c, **k: Done("", "Error: not logged in", 1), which=lambda: "codex")
    assert "結束碼 1" in str(info.value)
    with pytest.raises(LoginError) as info:
        ask("x", runner=lambda c, **k: Done("", "segfault", 2), which=lambda: "codex")
    assert type(info.value) is LoginError


def test_not_installed_and_timeout():
    with pytest.raises(NotInstalledError):
        ask("x", which=lambda: None)

    def boom(cmd, **kw):
        raise OSError("cannot run")

    with pytest.raises(NotInstalledError):
        ask("x", runner=boom, which=lambda: "codex")

    def slow(cmd, **kw):
        raise subprocess.TimeoutExpired(cmd, 1)

    with pytest.raises(CallTimeoutError):
        ask("x", timeout=1, runner=slow, which=lambda: "codex")


def test_scratch_dir_is_removed():
    seen, runner = capture()
    ask("x", runner=runner, which=lambda: "codex")
    assert not os.path.exists(seen["cwd"])
