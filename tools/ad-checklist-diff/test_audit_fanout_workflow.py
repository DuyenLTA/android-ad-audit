"""Run .claude/workflows/audit-fanout.mjs under Node with stubbed agent/pipeline.

The workflow host supplies agent(), pipeline(), phase(), log() and args at run
time, so the script cannot be imported. The harness wraps the script body in an
async function that takes those globals as parameters, which lets each test
decide what every agent "returns" and check where the run stops and what it
reports. Skipped when node is not installed.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / ".claude" / "workflows" / "audit-fanout.mjs"
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="node not installed")

# Reads the scenario from argv, runs the workflow body, prints one JSON line:
# {"ok": result} or {"error": message}, plus every agent label and prompt seen.
HARNESS = r"""
const fs = require('fs')
const [scriptPath, scenarioJson] = process.argv.slice(2)
const scenario = JSON.parse(scenarioJson)
const body = fs.readFileSync(scriptPath, 'utf8').replace(/^export const meta/m, 'const meta')
const run = new Function('args', 'agent', 'pipeline', 'parallel', 'phase', 'log',
  `return (async () => {\n${body}\n})()`)
const calls = []
const agent = async (prompt, opts) => {
  calls.push({ label: opts.label, prompt })
  if (opts.label === 'audit') return scenario.audit
  if (opts.label.startsWith('judge:')) return scenario.judge
  if (opts.label.startsWith('verify:')) return scenario.verify
  throw new Error('unexpected agent ' + opts.label)
}
const pipeline = async (items, ...stages) => Promise.all(items.map(async (item) => {
  let value = item
  for (const stage of stages) value = await stage(value)
  return value
}))
const parallel = async (fns) => Promise.all(fns.map((fn) => fn()))
run(scenario.args, agent, pipeline, parallel, () => {}, () => {})
  .then((ok) => console.log(JSON.stringify({ ok, calls })))
  .catch((e) => console.log(JSON.stringify({ error: String(e.message), calls })))
"""

PKG = "com.example.app"
BASE_ARGS = {"apps": [PKG], "python": "/repo/.venv/bin/python", "repoDir": "/repo"}


def run_workflow(tmp_path, args, audit=None, judge=None, verify=None):
    harness = tmp_path / "harness.cjs"
    harness.write_text(HARNESS, encoding="utf-8")
    scenario = json.dumps({"args": args, "audit": audit, "judge": judge, "verify": verify})
    out = subprocess.run([NODE, str(harness), str(SCRIPT), scenario],
                         capture_output=True, text=True, encoding="utf-8", timeout=60)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout.strip().splitlines()[-1])


def labels(result):
    return [c["label"] for c in result["calls"]]


def test_missing_python_stops_before_any_agent(tmp_path):
    args = {k: v for k, v in BASE_ARGS.items() if k != "python"}
    result = run_workflow(tmp_path, args)
    assert "Chưa có args.python" in result["error"]
    assert result["calls"] == []


def test_no_apps_stops_before_any_agent(tmp_path):
    result = run_workflow(tmp_path, {**BASE_ARGS, "apps": []})
    assert "Chưa có app nào" in result["error"]
    assert result["calls"] == []


def test_runner_failure_stops_before_judging(tmp_path):
    audit = {"exit_code": 1, "output": "Traceback ...", "apps": []}
    result = run_workflow(tmp_path, BASE_ARGS, audit=audit)
    assert "audit_runner.py không chạy được" in result["error"]
    assert labels(result) == ["audit"]


def test_dev_build_stops_before_judging(tmp_path):
    audit = {"exit_code": 3, "output": "build dev", "apps": []}
    result = run_workflow(tmp_path, BASE_ARGS, audit=audit)
    assert "Sai build" in result["error"]
    assert labels(result) == ["audit"]


def test_audit_command_names_only_the_requested_package(tmp_path):
    audit = {"exit_code": 0, "output": "", "apps": [{"package": PKG, "unsettled": 0}]}
    result = run_workflow(tmp_path, BASE_ARGS, audit=audit)
    prompt = result["calls"][0]["prompt"]
    assert f"/repo/.venv/bin/python tools/ad-checklist-diff/audit_runner.py --capture --package {PKG}" in prompt


def test_serial_reaches_the_audit_command(tmp_path):
    audit = {"exit_code": 0, "output": "", "apps": [{"package": PKG, "unsettled": 0}]}
    result = run_workflow(tmp_path, {**BASE_ARGS, "serial": "R58M123ABC"}, audit=audit)
    prompt = result["calls"][0]["prompt"]
    assert f"audit_runner.py --capture --serial R58M123ABC --package {PKG}" in prompt


def test_serial_with_shell_characters_is_refused(tmp_path):
    result = run_workflow(tmp_path, {**BASE_ARGS, "serial": "x; rm -rf /"})
    assert "serial không hợp lệ" in result["error"]
    assert labels(result) == []


def test_clean_app_opens_no_judge_or_verify_agent(tmp_path):
    audit = {"exit_code": 0, "output": "", "apps": [{"package": PKG, "unsettled": 0}]}
    result = run_workflow(tmp_path, BASE_ARGS, audit=audit)
    assert labels(result) == ["audit"]
    assert result["ok"]["clean"] == [PKG]
    assert result["ok"]["confirmed"] == []


def test_findings_split_into_confirmed_and_unresolved(tmp_path):
    audit = {"exit_code": 2, "output": "", "apps": [{"package": PKG, "unsettled": 2}]}
    judge = {"findings": [
        {"value": "ca-app-pub-1/111", "verdict": "lech"},
        {"value": "ca-app-pub-1/222", "verdict": "khong-ket-luan-duoc"},
    ]}
    verify = {"verdicts": [{"value": "ca-app-pub-1/111", "holds": True}], "tool_gap": ""}
    result = run_workflow(tmp_path, BASE_ARGS, audit=audit, judge=judge, verify=verify)
    assert labels(result) == ["audit", f"judge:{PKG}", f"verify:{PKG}"]
    ok = result["ok"]
    assert [f["value"] for f in ok["confirmed"]] == ["ca-app-pub-1/111"]
    assert [f["value"] for f in ok["unresolved"]] == ["ca-app-pub-1/222"]
    assert ok["disputed"] == []
