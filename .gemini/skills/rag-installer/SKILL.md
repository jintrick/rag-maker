---
name: rag-installer
description: Install one or more RAG knowledge bases into a target directory as separate subdirectories.
---

# rag-installer

Use this skill to install one or more RAG knowledge bases. Each selected KB will be placed in its own subdirectory within the target root, preserving its independence.

## Execution Steps

1. **Select Source(s)**: Run `ragmaker-ask-dir --multiple --initial-dir .` to select one or more source KB directories. Capture the result list as `SOURCES`.
2. **Select Destination**: Run `ragmaker-ask-dir --initial-dir .` to select the target root directory where the KBs should be installed. Capture as `TARGET_ROOT`.
3. **Confirmation**:
    - Inform the user: "Installing knowledge base(s) from `SOURCES` into `TARGET_ROOT`."
    - Clarify: "Each knowledge base will be installed into its own subdirectory (e.g., `TARGET_ROOT/source_name`)."
    - Wait for user confirmation.
4. **Install**: Run `ragmaker-install-kb --source SOURCES --target-kb-root TARGET_ROOT`.
    - Note: Do NOT use the `--merge` flag. The tool defaults to subdirectory installation.
    - Use `--force` only if the user explicitly approves overwriting existing directories.
5. **Open**: Parse the `target_kb_root` (or the specific installed path) from the JSON output and run `ragmaker-open-directory` to show the result.