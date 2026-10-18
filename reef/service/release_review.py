"""PawLogic's file, input and evaluation views, kept separate from Reef's page layout."""

from __future__ import annotations

import difflib
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlencode

from reef.service.page_chrome import escape
from reef.service.review_files import FilePreview


def diff_block(path: str, before: str, after: str, before_id: object, release_id: object) -> str:
    """A unified diff of the two exact version contents, including newly created and deleted files."""
    rendered = []
    lines = difflib.unified_diff(
        before.splitlines(),
        after.splitlines(),
        fromfile=f"{path} ({str(before_id or 'empty')[:8]})",
        tofile=f"{path} ({str(release_id or 'empty')[:8]})",
        lineterm="",
    )
    for index, line in enumerate(lines):
        if index < 2 or line.startswith("@@"):
            kind = "hunk"
        elif line.startswith("+"):
            kind = "add"
        elif line.startswith("-"):
            kind = "del"
        else:
            kind = "context"
        rendered.append(f'<span class="{kind}">{escape(line)}</span>')
    if not rendered:
        return f'<p class="empty">{escape(path)} is unchanged</p>'
    return '<pre class="diff">' + "".join(rendered) + "</pre>"


def file_changes(
    before: Mapping[str, str],
    after: Mapping[str, str],
    previews: Mapping[str, FilePreview],
    *,
    before_id: object,
    release_id: object,
) -> str:
    """Show file paths, exact diffs and an explicit read-only version preview."""
    changes = []
    for path in sorted(before.keys() | after.keys()):
        if before.get(path) == after.get(path):
            continue
        if path not in before:
            operation = "create"
        elif path not in after:
            operation = "remove"
        else:
            operation = "update"
        preview = previews.get(path)
        link = ""
        if preview is not None:
            side = "Baseline" if operation == "remove" else "Candidate"
            link = (
                f'<p><a class="tag" href="{escape(preview.cursor_url)}">Open in Cursor</a> '
                f'<span class="note">{side} read-only preview</span></p>'
                f'<p class="id">{escape(preview.path)}</p>'
            )
        content = after.get(path, before.get(path, ""))
        changes.append(
            f'<div class="change"><div class="change-head"><span class="tag operation-{operation}">{operation}</span>'
            f'<code class="id">{escape(path)}</code></div>{link}'
            + diff_block(path, before.get(path, ""), after.get(path, ""), before_id, release_id)
            + f"<details><summary>Full content</summary><pre>{escape(content)}</pre></details></div>"
        )
    return "".join(changes) or '<p class="empty">No file changes.</p>'


def input_html(metrics: Mapping[str, Any], step: int, query: Mapping[str, str], record_status: str) -> str:
    """Link actual retained model input and output without inventing explanations for old steps."""
    request = metrics.get("training_request")
    if isinstance(request, Mapping):
        mode = "Explicit training request"
        instruction = f'<pre>{escape(request.get("text", ""))}</pre>'
    else:
        mode = "Automatic record batch"
        instruction = '<p class="note">The proposer reads the recorded batch, not the Why fallback sentence.</p>'
    body = f'<p>{mode}</p>{instruction}<p>Recorded traces: {escape(metrics.get("traces", "Not recorded"))}</p>'
    if record_status == "retained":
        href = f"/reef/harness/releases/{step}/page?" + urlencode({**query, "record": "proposer.json"})
        body += f'<p><a href="{escape(href)}" target="_blank" rel="noopener">View recorded proposer input and output</a></p>'
        body += (
            '<p class="note">Contains the retained model messages and replies; original recording limits apply.</p>'
        )
    elif record_status == "unavailable":
        body += '<p class="empty">The retained proposer record could not be read.</p>'
    else:
        body += '<p class="empty">Proposer input was not retained for this step.</p>'
    return body


def evaluation_html(metrics: Mapping[str, Any], current_scoring: Mapping[str, str] | None = None) -> str:
    """Separate the selection policy, scoring implementation and individual task results."""
    selection = metrics.get("selection")
    if not isinstance(selection, Mapping):
        return '<p class="empty">No evaluation decision was recorded for this step.</p>'
    evaluation = selection.get("evaluation")
    evaluation = evaluation if isinstance(evaluation, Mapping) else {}
    measured = evaluation.get("metrics")
    measured = measured if isinstance(measured, Mapping) else metrics
    policy = str(selection.get("policy", "Not recorded"))
    body = f'<dl class="details"><div><dt>Selection policy</dt><dd>{escape(policy)}</dd></div>'
    body += f'<div><dt>Evaluator</dt><dd>{escape(evaluation.get("evaluator", "Not recorded"))}</dd></div></dl>'
    settings = selection.get("metrics")
    settings = settings if isinstance(settings, Mapping) else {}
    if policy == "score_comparison":
        margin = settings.get("min_win_margin", 0)
        body += f"<p>Selected when task-pair wins minus losses &gt; {escape(margin)}. Ties do not count as wins.</p>"
    elif policy == "floor":
        body += f'<p>Every candidate task must meet the floor: {escape(settings.get("floor_score"))}.</p>'
    rule = measured.get("scoring_rule")
    if isinstance(rule, Mapping):
        body += "<h3>Scorer recorded at evaluation time</h3>"
    else:
        rule = current_scoring or {}
        body += '<h3>Current deployment scorer</h3><p class="note">Historical scorer source was not recorded; this is the current configuration, not proof of the historical rule.</p>'
    body += f'<p class="id">{escape(rule.get("implementation", "Not recorded"))}</p>'
    if rule.get("description"):
        body += f'<p class="text">{escape(rule["description"])}</p>'
    if rule.get("source"):
        body += f'<details><summary>Scoring implementation</summary><pre>{escape(rule["source"])}</pre></details>'
    elif rule.get("source_status"):
        body += f'<p class="note">{escape(rule["source_status"])}</p>'
    candidates = measured.get("candidate_episodes", ())
    baselines = measured.get("current_episodes", ())
    current_scores = measured.get("current_scores", ())
    if not isinstance(candidates, (list, tuple)):
        candidates = ()
    if not isinstance(baselines, (list, tuple)):
        baselines = ()
    if not isinstance(current_scores, (list, tuple)):
        current_scores = ()
    scored = any(isinstance(episode, Mapping) and episode.get("score") is not None for episode in candidates)
    rows = []
    for index, episode in enumerate(candidates):
        if not isinstance(episode, Mapping):
            continue
        baseline = baselines[index] if index < len(baselines) and isinstance(baselines[index], Mapping) else {}
        old_score = baseline.get("score", current_scores[index] if index < len(current_scores) else "Not recorded")
        rows.append(
            f'<tr><td class="text">{escape(episode.get("task"))}</td><td>{escape(old_score)}</td>'
            f'<td>{escape(episode.get("score") if episode.get("score") is not None else "Not scored")}</td>'
            f'<td class="text">{escape(baseline.get("reply", "Not recorded"))}</td>'
            f'<td class="text">{escape(episode.get("reply"))}</td><td>{escape(episode.get("failure") or "")}</td></tr>'
        )
    if rows:
        candidate_heading = "Candidate score" if scored else "Candidate result"
        body += (
            '<div class="table-scroll" tabindex="0"><table><thead><tr><th>Task / input</th><th>Baseline score</th>'
            f"<th>{candidate_heading}</th><th>Baseline reply</th><th>Candidate reply</th><th>Episode failure</th></tr></thead>"
            f'<tbody>{"".join(rows)}</tbody></table></div>'
            '<p class="note">These are the retained episode summaries. Scores measure these tasks only, not all Skill behavior.</p>'
        )
    else:
        body += '<p class="empty">Per-task results were not recorded.</p>'
    return body
