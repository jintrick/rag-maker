---
name: rag-installer
description: Install or migrate a RAG knowledge base using ragmaker-ask-dir and ragmaker-install-kb.
---

# rag-installer

Use this skill to install a RAG knowledge base. Execute these commands exactly:

1. **Select Source**: Run `ragmaker-ask-dir` to select the source KB directory. Capture as `SOURCE`.
2. **Select Destination**: Run `ragmaker-ask-dir --initial-dir .` to select the parent directory where the KB should be placed. Capture as `DEST_PARENT`.
3. **Confirmation**:
    - Inform the user: "Installing knowledge base from `SOURCE` into `DEST_PARENT`."
    - Note that the tool will automatically create a sub-folder with the same name as the source.
    - Wait for user confirmation.
4. **Install**: Run `ragmaker-install-kb --source SOURCE --target-kb-root DEST_PARENT`. (Add `--force` if the user confirms overwriting).
5. **Open**: Parse the `target_kb_root` from the JSON output of the install command and run `ragmaker-open-directory` with it.