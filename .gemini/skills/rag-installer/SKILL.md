---
name: rag-installer
description: Install or merge RAG knowledge bases using ragmaker-ask-dir and ragmaker-install-kb.
---

# rag-installer

Use this skill to install or merge one or more RAG knowledge bases. Execute these commands exactly:

1. **Select Source(s)**: Run `ragmaker-ask-dir --multiple --initial-dir .` to select one or more source KB directories. Capture the result list as `SOURCES`.
2. **Select Destination**: Run `ragmaker-ask-dir --initial-dir .` to select the target directory where the KB(s) should be installed or merged. Capture as `TARGET_ROOT`.
3. **Confirmation**:
    - Inform the user: "Installing/Merging knowledge base(s) from `SOURCES` into `TARGET_ROOT`."
    - Note that if `TARGET_ROOT` already contains a knowledge base, the new documents and metadata will be merged non-destructively.
    - Wait for user confirmation.
4. **Install**: Run `ragmaker-install-kb --source SOURCES --target-kb-root TARGET_ROOT`. (Add `--force` if the user confirms merging into a non-empty directory).
5. **Open**: Parse the `target_kb_root` from the successful JSON output and run `ragmaker-open-directory` with it.
