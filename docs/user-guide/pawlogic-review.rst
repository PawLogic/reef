PawLogic harness review
======================

This fork adds file review to the native ``/versions <version>`` page.
It preserves Reef's evaluation, selection and explicit install flow.

Review Skill files
------------------

``What changed`` shows Skill file paths and a diff against the release the
candidate ran on. New files show added lines. Removed files show deleted
lines. ``Full content`` shows the complete file.

``Open in Cursor`` opens a read-only temporary copy of the selected version,
including its Skill support files. It does not open or overwrite installed
skills or Reef's artifact cache. The temporary copy remains available until
the operating system cleans its temporary directory.

For a remote Reef service, set its SSH destination before starting it::

   REEF_REVIEW_SSH_URL=ssh://user@host:2222 reef serve -c deployment.yaml

An individual page can also carry ``ssh=ssh%3A%2F%2Fuser%40host%3A2222`` in
its query. This takes precedence over the service setting and travels with
the page's version links. Cursor runs on the browsing machine and needs its
Remote SSH extension. HTTP port forwarding and Cursor's SSH connection are
separate connections; preserve the existing ``scenario`` and ``key`` query
parameters when changing the HTTP origin for a tunnel.

With no SSH destination, Cursor opens the preview on the browsing machine.
Use this mode only when Reef runs on that same machine.

Inspect inputs and scoring
--------------------------

``Input`` identifies an explicit request or an automatic batch. When the step
retained ``proposer.json``, its link opens the recorded model messages and
replies using the same scenario-scoped page authorization. Recording limits
and redaction still apply. The page does not reconstruct missing input.

``Evaluation`` separates the selection policy from the episode scorer. It
shows the tasks, baseline and candidate scores, and retained replies. New
evaluations also record the scorer's class and available source. An older
step labels the current deployment's scorer separately: that source does
not establish what scored a historical step. A scorer can call other
functions or services; its class source alone does not include those dependencies.

Generated Skill language
------------------------

New and revised model-generated Skill descriptions and bodies use Simplified
Chinese. Names and identifiers remain English. Commands, code, protocol
literals and exact expected outputs retain their required form. Existing
records, unmodified skills, fallback messages and HTML labels stay unchanged.
