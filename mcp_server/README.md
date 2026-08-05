# OrgMemory MCP server

The stdio server exposes company memory to Cursor and other MCP clients. Configure a client to run `make -C /absolute/path/to/runbook mcp` with `RUNBOOK_API_URL` and a workspace-scoped `RUNBOOK_API_KEY` (legacy environment names remain compatible).

Preferred tools:

- `orgmemory_ingest_github_repo`
- `orgmemory_ingest_slack_channel`
- `orgmemory_upload_source`
- `orgmemory_ask`
- `orgmemory_search_memories`
- `orgmemory_get_company_profile`
- `orgmemory_get_project_profile`
- `orgmemory_get_service_profile`
- `orgmemory_get_memory_graph`
- `orgmemory_list_memory_conflicts`
- `orgmemory_list_memory_updates`
- `orgmemory_list_source_revisions`
- `orgmemory_list_change_sets`
- `orgmemory_compile_skill`
- `orgmemory_list_skills`
- `orgmemory_create_work`
- `orgmemory_list_work`
- `orgmemory_get_work`
- `orgmemory_resolve_work_step`
- `orgmemory_complete_work_step`

All answers, profiles, and work packages come from source-backed memory and include retrieval lineage. `orgmemory_create_work` prepares a portable agent packet. Consequential connector steps stay in `pending_approval` until `orgmemory_resolve_work_step` approves them; a worker reports the exact outcome through `orgmemory_complete_work_step`.

Legacy `runbook_*` tools remain available during migration but represent advanced compatibility features, not the primary product surface.
