# Oversized Test File Split Plan

## Purpose

This document plans future oversized test-file splits using current repo data.
It does not move files, rewrite assertions, extract helpers, or change CI.

## Roadmap context

- Issue: #3983
- Parent tracker: #2523
- Follows #3973 / #3982, the report-only order-sensitivity diagnostics slice.

## Methodology

Metrics were generated from the current test tree using:

- physical line counts for every recursive `test_*.py` file under `tests/`;
- AST counts for `test_*` functions and `Test*` classes;
- one `pytest --collect-only -q tests` run to count collected items per file;
- current taxonomy classification from `tests._taxonomy.classify_test_path`; and
- static setup-signal scans for route/API, DB/session, import-state, security, filesystem, subprocess/script, async/threading, and UI/static indicators.

Static signals are not proof of risk. They are review prompts.
Future split PRs must still inspect each file manually before editing.

## Current summary

- test files scanned: 698
- collected pytest items counted: 4436
- large-file threshold: 300 lines
- large-collected threshold: 20 collected items

Area distribution:

| Value | Files |
|---|---:|
| cli | 29 |
| helpers | 1 |
| js | 48 |
| routes | 30 |
| security | 84 |
| services | 183 |
| uncategorized | 284 |
| unit | 39 |

Sub-area distribution:

| Value | Files |
|---|---:|
| api | 8 |
| atomic | 3 |
| auth | 11 |
| calendar | 13 |
| cli | 29 |
| confinement | 8 |
| cookbook | 19 |
| document | 12 |
| email | 17 |
| embedding | 6 |
| gallery | 6 |
| history | 3 |
| js | 48 |
| llm | 20 |
| mcp | 11 |
| memory | 16 |
| nondict | 7 |
| nonstring | 22 |
| owner | 15 |
| owner_scope | 25 |
| parse | 5 |
| provider | 15 |
| research | 16 |
| route | 6 |
| routes | 14 |
| scheduler | 4 |
| scope | 5 |
| security | 10 |
| session | 17 |
| ssrf | 3 |
| webhook | 3 |
| xss | 5 |

Values below 2 files: 296 values covering 296 files.

## Top files by collected pytest items

| File | Lines | Collected tests | Test defs | Test classes | Area | Sub-area | Signals |
|---|---:|---:|---:|---:|---|---|---|
| `tests/test_model_routes.py` | 1792 | 147 | 118 | 10 | routes | routes | route/api, db/session, import-state, async/threading |
| `tests/test_security_regressions.py` | 1515 | 98 | 74 | 0 | security | security | route/api, db/session, import-state, security, filesystem, async/threading, ui/static |
| `tests/test_cookbook_helpers.py` | 958 | 69 | 69 | 0 | services | cookbook | route/api, filesystem, subprocess/script, async/threading, ui/static |
| `tests/test_shell_routes.py` | 538 | 69 | 53 | 9 | routes | routes | route/api, import-state, filesystem |
| `tests/test_endpoint_probing.py` | 497 | 61 | 36 | 7 | uncategorized | endpoint_probing | route/api, db/session, import-state |
| `tests/test_pr_blocker_audit.py` | 964 | 58 | 58 | 0 | uncategorized | pr_blocker_audit | import-state, security, filesystem |
| `tests/test_agent_loop.py` | 500 | 54 | 54 | 5 | uncategorized | agent_loop | db/session, import-state |
| `tests/test_run_focus.py` | 450 | 53 | 50 | 0 | uncategorized | run_focus | security, filesystem, subprocess/script, ui/static |
| `tests/test_service_health.py` | 472 | 47 | 42 | 0 | uncategorized | service_health | async/threading |
| `tests/test_research_routes_path_confinement.py` | 273 | 46 | 14 | 0 | security | confinement | route/api, filesystem, async/threading |
| `tests/test_manage_mcp_command_allowlist.py` | 168 | 45 | 10 | 0 | services | mcp | db/session, subprocess/script, async/threading, ui/static |
| `tests/test_provider_classification.py` | 115 | 42 | 9 | 2 | services | provider | - |
| `tests/test_review_regressions.py` | 1326 | 39 | 39 | 0 | uncategorized | review_regressions | route/api, db/session, import-state, filesystem, async/threading |
| `tests/test_chat_helpers.py` | 562 | 36 | 23 | 0 | uncategorized | chat_helpers | route/api, filesystem, async/threading |
| `tests/test_model_context.py` | 314 | 36 | 34 | 4 | uncategorized | model_context | db/session, import-state |
| `tests/test_llm_core_anthropic_temp_omit.py` | 94 | 32 | 6 | 0 | services | llm | db/session |
| `tests/test_redos_verdict_continuation.py` | 80 | 30 | 5 | 0 | uncategorized | redos_verdict_continuation | route/api |
| `tests/test_upload_limits_centralized.py` | 110 | 29 | 5 | 0 | uncategorized | upload_limits_centralized | import-state, filesystem |
| `tests/test_email_oauth.py` | 580 | 28 | 25 | 0 | services | email | route/api, db/session, security, async/threading |
| `tests/test_cookbook_docker_access.py` | 339 | 28 | 13 | 0 | services | cookbook | route/api, filesystem, async/threading |
| `tests/test_rename_user_owner_sync.py` | 740 | 27 | 27 | 0 | security | owner | route/api, db/session, import-state, filesystem, async/threading |
| `tests/test_taxonomy.py` | 151 | 27 | 17 | 0 | uncategorized | taxonomy | security, ui/static |
| `tests/test_endpoint_resolver_urls.py` | 95 | 27 | 23 | 3 | uncategorized | endpoint_resolver_urls | - |
| `tests/test_helpers_import_state.py` | 426 | 26 | 26 | 0 | helpers | helpers | route/api, db/session, import-state |
| `tests/test_tool_path_confinement.py` | 303 | 25 | 25 | 0 | security | confinement | import-state, filesystem, async/threading |
| `tests/test_provider_endpoints_url_building.py` | 86 | 25 | 3 | 0 | services | provider | - |
| `tests/test_llm_core_temperature_reasoning.py` | 111 | 24 | 8 | 0 | services | llm | - |
| `tests/test_bg_job_tools.py` | 174 | 23 | 16 | 0 | uncategorized | bg_job_tools | filesystem, async/threading |
| `tests/test_copilot.py` | 170 | 23 | 16 | 0 | uncategorized | copilot | - |
| `tests/test_research_utils.py` | 97 | 23 | 23 | 2 | services | research | - |

## Top files by physical line count

| File | Lines | Collected tests | Test defs | Test classes | Area | Sub-area | Signals |
|---|---:|---:|---:|---:|---|---|---|
| `tests/test_model_routes.py` | 1792 | 147 | 118 | 10 | routes | routes | route/api, db/session, import-state, async/threading |
| `tests/test_security_regressions.py` | 1515 | 98 | 74 | 0 | security | security | route/api, db/session, import-state, security, filesystem, async/threading, ui/static |
| `tests/test_review_regressions.py` | 1326 | 39 | 39 | 0 | uncategorized | review_regressions | route/api, db/session, import-state, filesystem, async/threading |
| `tests/test_pr_blocker_audit.py` | 964 | 58 | 58 | 0 | uncategorized | pr_blocker_audit | import-state, security, filesystem |
| `tests/test_cookbook_helpers.py` | 958 | 69 | 69 | 0 | services | cookbook | route/api, filesystem, subprocess/script, async/threading, ui/static |
| `tests/test_rename_user_owner_sync.py` | 740 | 27 | 27 | 0 | security | owner | route/api, db/session, import-state, filesystem, async/threading |
| `tests/test_email_owner_scope.py` | 607 | 12 | 12 | 0 | security | owner_scope | route/api, db/session, filesystem, async/threading |
| `tests/test_email_oauth.py` | 580 | 28 | 25 | 0 | services | email | route/api, db/session, security, async/threading |
| `tests/test_api_token_routes.py` | 578 | 17 | 17 | 0 | routes | api_routes | route/api, db/session, import-state, async/threading |
| `tests/test_chat_helpers.py` | 562 | 36 | 23 | 0 | uncategorized | chat_helpers | route/api, filesystem, async/threading |
| `tests/test_shell_routes.py` | 538 | 69 | 53 | 9 | routes | routes | route/api, import-state, filesystem |
| `tests/test_agent_loop.py` | 500 | 54 | 54 | 5 | uncategorized | agent_loop | db/session, import-state |
| `tests/test_endpoint_probing.py` | 497 | 61 | 36 | 7 | uncategorized | endpoint_probing | route/api, db/session, import-state |
| `tests/test_service_health.py` | 472 | 47 | 42 | 0 | uncategorized | service_health | async/threading |
| `tests/test_kv_cache_invalidation_2927.py` | 463 | 8 | 8 | 0 | uncategorized | kv_cache_invalidation_2927 | route/api, db/session, import-state, async/threading |
| `tests/test_run_focus.py` | 450 | 53 | 50 | 0 | uncategorized | run_focus | security, filesystem, subprocess/script, ui/static |
| `tests/test_helpers_import_state.py` | 426 | 26 | 26 | 0 | helpers | helpers | route/api, db/session, import-state |
| `tests/test_endpoint_owner_scope_followup.py` | 414 | 11 | 11 | 0 | security | owner_scope | route/api, db/session, filesystem |
| `tests/test_api_chat_security.py` | 404 | 22 | 8 | 0 | security | security | route/api, db/session, import-state, filesystem, async/threading |
| `tests/test_imap_leak_fixes.py` | 404 | 15 | 15 | 0 | uncategorized | imap_leak_fixes | route/api, db/session, security, filesystem |
| `tests/test_companion_readonly.py` | 402 | 17 | 17 | 0 | uncategorized | companion_readonly | db/session, import-state |
| `tests/test_upload_handler_atomicity.py` | 401 | 9 | 9 | 0 | uncategorized | upload_handler_atomicity | filesystem, async/threading |
| `tests/test_workspace_confine.py` | 387 | 20 | 20 | 0 | uncategorized | workspace_confine | route/api, filesystem, subprocess/script, async/threading |
| `tests/test_auth_regressions.py` | 375 | 15 | 15 | 0 | security | auth | route/api, db/session, import-state, async/threading |
| `tests/test_tool_policy.py` | 360 | 14 | 14 | 0 | uncategorized | tool_policy | import-state, async/threading |
| `tests/test_fenced_example_not_executed_for_native_models.py` | 345 | 18 | 18 | 0 | uncategorized | fenced_example_not_executed_for_native_models | async/threading |
| `tests/test_calendar_owner_scope.py` | 345 | 7 | 7 | 0 | security | owner_scope | route/api, db/session, import-state, filesystem, async/threading, ui/static |
| `tests/test_upload_routes_owner_scope.py` | 344 | 13 | 13 | 0 | security | owner_scope | route/api, filesystem, async/threading |
| `tests/test_agent_migration_manifest.py` | 340 | 15 | 15 | 0 | uncategorized | agent_migration_manifest | import-state, filesystem |
| `tests/test_cookbook_docker_access.py` | 339 | 28 | 13 | 0 | services | cookbook | route/api, filesystem, async/threading |

## Split planning candidates

This section is generated from metrics, not from manual judgement.
Files are included when they meet at least one threshold:

- at least 300 physical lines; or
- at least 20 collected pytest items.

These are planning candidates only. A later split PR still needs a focused manual review of each file before moving tests.

| File | Why included | Setup/risk signals | Suggested handling |
|---|---|---|---|
| `tests/test_model_routes.py` | 1792 lines, 147 collected tests | route/api, db/session, import-state, async/threading | Defer mechanical split until setup/risk boundaries are mapped. |
| `tests/test_security_regressions.py` | 1515 lines, 98 collected tests | route/api, db/session, import-state, security, filesystem, async/threading, ui/static | Defer mechanical split until setup/risk boundaries are mapped. |
| `tests/test_cookbook_helpers.py` | 958 lines, 69 collected tests | route/api, filesystem, subprocess/script, async/threading, ui/static | Defer mechanical split until setup/risk boundaries are mapped. |
| `tests/test_shell_routes.py` | 538 lines, 69 collected tests | route/api, import-state, filesystem | Defer mechanical split until setup/risk boundaries are mapped. |
| `tests/test_endpoint_probing.py` | 497 lines, 61 collected tests | route/api, db/session, import-state | Defer mechanical split until setup/risk boundaries are mapped. |
| `tests/test_pr_blocker_audit.py` | 964 lines, 58 collected tests | import-state, security, filesystem | Defer mechanical split until setup/risk boundaries are mapped. |
| `tests/test_agent_loop.py` | 500 lines, 54 collected tests | db/session, import-state | Defer mechanical split until setup/risk boundaries are mapped. |
| `tests/test_run_focus.py` | 450 lines, 53 collected tests | security, filesystem, subprocess/script, ui/static | Defer mechanical split until setup/risk boundaries are mapped. |
| `tests/test_service_health.py` | 472 lines, 47 collected tests | async/threading | Good first manual-review candidate if test themes are cohesive. |
| `tests/test_research_routes_path_confinement.py` | 46 collected tests | route/api, filesystem, async/threading | Defer mechanical split until setup/risk boundaries are mapped. |
| `tests/test_manage_mcp_command_allowlist.py` | 45 collected tests | db/session, subprocess/script, async/threading, ui/static | Defer mechanical split until setup/risk boundaries are mapped. |
| `tests/test_provider_classification.py` | 42 collected tests | No obvious setup signals from static scan. | Good first manual-review candidate if test themes are cohesive. |
| `tests/test_review_regressions.py` | 1326 lines, 39 collected tests | route/api, db/session, import-state, filesystem, async/threading | Defer mechanical split until setup/risk boundaries are mapped. |
| `tests/test_chat_helpers.py` | 562 lines, 36 collected tests | route/api, filesystem, async/threading | Defer mechanical split until setup/risk boundaries are mapped. |
| `tests/test_model_context.py` | 314 lines, 36 collected tests | db/session, import-state | Defer mechanical split until setup/risk boundaries are mapped. |
| `tests/test_llm_core_anthropic_temp_omit.py` | 32 collected tests | db/session | Defer mechanical split until setup/risk boundaries are mapped. |
| `tests/test_redos_verdict_continuation.py` | 30 collected tests | route/api | Defer mechanical split until setup/risk boundaries are mapped. |
| `tests/test_upload_limits_centralized.py` | 29 collected tests | import-state, filesystem | Defer mechanical split until setup/risk boundaries are mapped. |
| `tests/test_email_oauth.py` | 580 lines, 28 collected tests | route/api, db/session, security, async/threading | Defer mechanical split until setup/risk boundaries are mapped. |
| `tests/test_cookbook_docker_access.py` | 339 lines, 28 collected tests | route/api, filesystem, async/threading | Defer mechanical split until setup/risk boundaries are mapped. |
| `tests/test_rename_user_owner_sync.py` | 740 lines, 27 collected tests | route/api, db/session, import-state, filesystem, async/threading | Defer mechanical split until setup/risk boundaries are mapped. |
| `tests/test_taxonomy.py` | 27 collected tests | security, ui/static | Defer mechanical split until setup/risk boundaries are mapped. |
| `tests/test_endpoint_resolver_urls.py` | 27 collected tests | No obvious setup signals from static scan. | Good first manual-review candidate if test themes are cohesive. |
| `tests/test_helpers_import_state.py` | 426 lines, 26 collected tests | route/api, db/session, import-state | Defer mechanical split until setup/risk boundaries are mapped. |
| `tests/test_tool_path_confinement.py` | 303 lines, 25 collected tests | import-state, filesystem, async/threading | Defer mechanical split until setup/risk boundaries are mapped. |
| `tests/test_provider_endpoints_url_building.py` | 25 collected tests | No obvious setup signals from static scan. | Good first manual-review candidate if test themes are cohesive. |
| `tests/test_llm_core_temperature_reasoning.py` | 24 collected tests | No obvious setup signals from static scan. | Good first manual-review candidate if test themes are cohesive. |
| `tests/test_bg_job_tools.py` | 23 collected tests | filesystem, async/threading | Good first manual-review candidate if test themes are cohesive. |
| `tests/test_copilot.py` | 23 collected tests | No obvious setup signals from static scan. | Good first manual-review candidate if test themes are cohesive. |
| `tests/test_research_utils.py` | 23 collected tests | No obvious setup signals from static scan. | Good first manual-review candidate if test themes are cohesive. |
| `tests/test_api_chat_security.py` | 404 lines, 22 collected tests | route/api, db/session, import-state, filesystem, async/threading | Defer mechanical split until setup/risk boundaries are mapped. |
| `tests/test_tool_support_heuristic.py` | 22 collected tests | No obvious setup signals from static scan. | Good first manual-review candidate if test themes are cohesive. |
| `tests/test_platform_compat.py` | 322 lines, 21 collected tests | import-state, filesystem, subprocess/script | Defer mechanical split until setup/risk boundaries are mapped. |
| `tests/test_context_compactor.py` | 21 collected tests | db/session, import-state, async/threading | Defer mechanical split until setup/risk boundaries are mapped. |
| `tests/test_fenced_inline_args.py` | 21 collected tests | db/session, import-state | Defer mechanical split until setup/risk boundaries are mapped. |
| `tests/test_cache_affinity_local_only.py` | 21 collected tests | No obvious setup signals from static scan. | Good first manual-review candidate if test themes are cohesive. |
| `tests/test_workspace_confine.py` | 387 lines, 20 collected tests | route/api, filesystem, subprocess/script, async/threading | Defer mechanical split until setup/risk boundaries are mapped. |
| `tests/test_null_owner_gates.py` | 332 lines, 20 collected tests | route/api, db/session, import-state | Defer mechanical split until setup/risk boundaries are mapped. |
| `tests/test_gallery_endpoint_hardening.py` | 326 lines, 20 collected tests | route/api, security, filesystem, ui/static | Defer mechanical split until setup/risk boundaries are mapped. |
| `tests/test_redos_llm_parsers.py` | 20 collected tests | No obvious setup signals from static scan. | Good first manual-review candidate if test themes are cohesive. |
| `tests/test_youtube_handler_consolidation.py` | 20 collected tests | route/api, import-state | Defer mechanical split until setup/risk boundaries are mapped. |
| `tests/test_fenced_example_not_executed_for_native_models.py` | 345 lines | async/threading | Plan split boundaries before editing. |
| `tests/test_api_token_routes.py` | 578 lines | route/api, db/session, import-state, async/threading | Defer mechanical split until setup/risk boundaries are mapped. |
| `tests/test_companion_readonly.py` | 402 lines | db/session, import-state | Defer mechanical split until setup/risk boundaries are mapped. |
| `tests/test_set_admin.py` | 317 lines | route/api, import-state, filesystem, async/threading | Defer mechanical split until setup/risk boundaries are mapped. |
| `tests/test_llm_core_ollama.py` | 324 lines | async/threading | Plan split boundaries before editing. |
| `tests/test_imap_leak_fixes.py` | 404 lines | route/api, db/session, security, filesystem | Defer mechanical split until setup/risk boundaries are mapped. |
| `tests/test_auth_regressions.py` | 375 lines | route/api, db/session, import-state, async/threading | Defer mechanical split until setup/risk boundaries are mapped. |
| `tests/test_agent_migration_manifest.py` | 340 lines | import-state, filesystem | Defer mechanical split until setup/risk boundaries are mapped. |
| `tests/test_calendar_recurrence.py` | 327 lines | No obvious setup signals from static scan. | Plan split boundaries before editing. |
| `tests/test_tool_policy.py` | 360 lines | import-state, async/threading | Defer mechanical split until setup/risk boundaries are mapped. |
| `tests/test_diffusion_server_security.py` | 325 lines | route/api, import-state, security, filesystem, async/threading, ui/static | Defer mechanical split until setup/risk boundaries are mapped. |
| `tests/test_upload_routes_owner_scope.py` | 344 lines | route/api, filesystem, async/threading | Defer mechanical split until setup/risk boundaries are mapped. |
| `tests/test_email_owner_scope.py` | 607 lines | route/api, db/session, filesystem, async/threading | Defer mechanical split until setup/risk boundaries are mapped. |
| `tests/test_endpoint_owner_scope_followup.py` | 414 lines | route/api, db/session, filesystem | Defer mechanical split until setup/risk boundaries are mapped. |
| `tests/test_upload_handler_atomicity.py` | 401 lines | filesystem, async/threading | Plan split boundaries before editing. |
| `tests/test_kv_cache_invalidation_2927.py` | 463 lines | route/api, db/session, import-state, async/threading | Defer mechanical split until setup/risk boundaries are mapped. |
| `tests/test_calendar_owner_scope.py` | 345 lines | route/api, db/session, import-state, filesystem, async/threading, ui/static | Defer mechanical split until setup/risk boundaries are mapped. |
| `tests/test_skills_manager_owner_isolation.py` | 306 lines | import-state, filesystem | Defer mechanical split until setup/risk boundaries are mapped. |

## Taxonomy coverage gaps among split candidates

`uncategorized` is a current taxonomy area, not a builder failure.
This plan does not reclassify tests because taxonomy changes should be reviewed separately from oversized-file split planning.

Before using any of these files as a split target, first decide whether the taxonomy should be refined in a separate focused issue/PR.

| File | Lines | Collected tests | Sub-area | Signals | Suggested follow-up |
|---|---:|---:|---|---|---|
| `tests/test_endpoint_probing.py` | 497 | 61 | endpoint_probing | route/api, db/session, import-state | Review taxonomy and setup/risk boundaries before any split. |
| `tests/test_pr_blocker_audit.py` | 964 | 58 | pr_blocker_audit | import-state, security, filesystem | Review taxonomy and setup/risk boundaries before any split. |
| `tests/test_agent_loop.py` | 500 | 54 | agent_loop | db/session, import-state | Review taxonomy and setup/risk boundaries before any split. |
| `tests/test_run_focus.py` | 450 | 53 | run_focus | security, filesystem, subprocess/script, ui/static | Review taxonomy and setup/risk boundaries before any split. |
| `tests/test_service_health.py` | 472 | 47 | service_health | async/threading | Review taxonomy mapping before using as a split target. |
| `tests/test_review_regressions.py` | 1326 | 39 | review_regressions | route/api, db/session, import-state, filesystem, async/threading | Review taxonomy and setup/risk boundaries before any split. |
| `tests/test_chat_helpers.py` | 562 | 36 | chat_helpers | route/api, filesystem, async/threading | Review taxonomy and setup/risk boundaries before any split. |
| `tests/test_model_context.py` | 314 | 36 | model_context | db/session, import-state | Review taxonomy and setup/risk boundaries before any split. |
| `tests/test_redos_verdict_continuation.py` | 80 | 30 | redos_verdict_continuation | route/api | Review taxonomy and setup/risk boundaries before any split. |
| `tests/test_upload_limits_centralized.py` | 110 | 29 | upload_limits_centralized | import-state, filesystem | Review taxonomy and setup/risk boundaries before any split. |
| `tests/test_taxonomy.py` | 151 | 27 | taxonomy | security, ui/static | Review taxonomy and setup/risk boundaries before any split. |
| `tests/test_endpoint_resolver_urls.py` | 95 | 27 | endpoint_resolver_urls | - | Review taxonomy mapping before using as a split target. |
| `tests/test_bg_job_tools.py` | 174 | 23 | bg_job_tools | filesystem, async/threading | Review taxonomy mapping before using as a split target. |
| `tests/test_copilot.py` | 170 | 23 | copilot | - | Review taxonomy mapping before using as a split target. |
| `tests/test_tool_support_heuristic.py` | 166 | 22 | tool_support_heuristic | - | Review taxonomy mapping before using as a split target. |
| `tests/test_platform_compat.py` | 322 | 21 | platform_compat | import-state, filesystem, subprocess/script | Review taxonomy and setup/risk boundaries before any split. |
| `tests/test_context_compactor.py` | 233 | 21 | context_compactor | db/session, import-state, async/threading | Review taxonomy and setup/risk boundaries before any split. |
| `tests/test_fenced_inline_args.py` | 186 | 21 | fenced_inline_args | db/session, import-state | Review taxonomy and setup/risk boundaries before any split. |
| `tests/test_cache_affinity_local_only.py` | 104 | 21 | cache_affinity_local_only | - | Review taxonomy mapping before using as a split target. |
| `tests/test_workspace_confine.py` | 387 | 20 | workspace_confine | route/api, filesystem, subprocess/script, async/threading | Review taxonomy and setup/risk boundaries before any split. |
| `tests/test_youtube_handler_consolidation.py` | 104 | 20 | youtube_handler_consolidation | route/api, import-state | Review taxonomy and setup/risk boundaries before any split. |
| `tests/test_fenced_example_not_executed_for_native_models.py` | 345 | 18 | fenced_example_not_executed_for_native_models | async/threading | Review taxonomy mapping before using as a split target. |
| `tests/test_companion_readonly.py` | 402 | 17 | companion_readonly | db/session, import-state | Review taxonomy and setup/risk boundaries before any split. |
| `tests/test_set_admin.py` | 317 | 17 | set_admin | route/api, import-state, filesystem, async/threading | Review taxonomy and setup/risk boundaries before any split. |
| `tests/test_imap_leak_fixes.py` | 404 | 15 | imap_leak_fixes | route/api, db/session, security, filesystem | Review taxonomy and setup/risk boundaries before any split. |
| `tests/test_agent_migration_manifest.py` | 340 | 15 | agent_migration_manifest | import-state, filesystem | Review taxonomy and setup/risk boundaries before any split. |
| `tests/test_tool_policy.py` | 360 | 14 | tool_policy | import-state, async/threading | Review taxonomy and setup/risk boundaries before any split. |
| `tests/test_upload_handler_atomicity.py` | 401 | 9 | upload_handler_atomicity | filesystem, async/threading | Review taxonomy mapping before using as a split target. |
| `tests/test_kv_cache_invalidation_2927.py` | 463 | 8 | kv_cache_invalidation_2927 | route/api, db/session, import-state, async/threading | Review taxonomy and setup/risk boundaries before any split. |

## Suggested first manual-review candidates

These are not automatic split approvals. They are categorized candidates with enough size/collection value and no route/API, DB/session, import-state, or security signal from the static scan.

Files still in the `uncategorized` taxonomy area are listed separately below so taxonomy review does not get mixed into the first split decision.

| File | Lines | Collected tests | Area | Sub-area | Signals | Why this is a candidate |
|---|---:|---:|---|---|---|---|
| `tests/test_provider_classification.py` | 115 | 42 | services | provider | - | 42 collected tests |
| `tests/test_provider_endpoints_url_building.py` | 86 | 25 | services | provider | - | 25 collected tests |
| `tests/test_llm_core_temperature_reasoning.py` | 111 | 24 | services | llm | - | 24 collected tests |
| `tests/test_research_utils.py` | 97 | 23 | services | research | - | 23 collected tests |
| `tests/test_redos_llm_parsers.py` | 201 | 20 | services | llm | - | 20 collected tests |
| `tests/test_llm_core_ollama.py` | 324 | 16 | services | llm | async/threading | 324 lines |
| `tests/test_calendar_recurrence.py` | 327 | 15 | services | calendar | - | 327 lines |

## High-risk candidates to defer first

These files may still be split later, but not as the first implementation slice without a separate manual boundary review.

| File | Lines | Collected tests | High-risk signals |
|---|---:|---:|---|
| `tests/test_model_routes.py` | 1792 | 147 | db/session, import-state, route/api |
| `tests/test_security_regressions.py` | 1515 | 98 | db/session, import-state, route/api, security |
| `tests/test_cookbook_helpers.py` | 958 | 69 | route/api |
| `tests/test_shell_routes.py` | 538 | 69 | import-state, route/api |
| `tests/test_endpoint_probing.py` | 497 | 61 | db/session, import-state, route/api |
| `tests/test_pr_blocker_audit.py` | 964 | 58 | import-state, security |
| `tests/test_agent_loop.py` | 500 | 54 | db/session, import-state |
| `tests/test_run_focus.py` | 450 | 53 | security |
| `tests/test_research_routes_path_confinement.py` | 273 | 46 | route/api |
| `tests/test_manage_mcp_command_allowlist.py` | 168 | 45 | db/session |
| `tests/test_review_regressions.py` | 1326 | 39 | db/session, import-state, route/api |
| `tests/test_chat_helpers.py` | 562 | 36 | route/api |
| `tests/test_model_context.py` | 314 | 36 | db/session, import-state |
| `tests/test_llm_core_anthropic_temp_omit.py` | 94 | 32 | db/session |
| `tests/test_redos_verdict_continuation.py` | 80 | 30 | route/api |

## Rules for future split PRs

- One file or one coherent file-family per PR.
- No assertion rewrites mixed with file moves.
- No helper extraction mixed with file moves.
- No production code changes.
- No CI workflow changes.
- Preserve existing markers and taxonomy unless the split issue explicitly says otherwise.
- Validate the original file's collected tests before and after the split.
- Validate any neighboring taxonomy/focused-runner behavior if paths change.
- Treat files with route/API, DB/session, import-state, or security signals as higher-risk until manually reviewed.

## Suggested next step

Use this plan to choose the first actual oversized-file split issue.
The first split should prefer a file with high review value and low setup risk.
Do not start a split PR from this planning issue alone if the file's boundaries are still ambiguous.

## Reproduction command

This document was generated with:

```bash
.venv/bin/python tests/tools/build_oversized_test_split_plan.py
```

## Freshness check

After editing the builder or rebasing the branch, regenerate the plan and confirm no unexpected plan drift:

```bash
.venv/bin/python tests/tools/build_oversized_test_split_plan.py
git diff --exit-code -- tests/OVERSIZED_TEST_SPLIT_PLAN.md
```
