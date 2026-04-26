---
trigger: glob
globs:
  - skills/**/*.md
  - agents/**/*.md
  - hooks/scripts/**/*.cjs
  - tools/**/*.cjs
---
**警告**: プロジェクトのルートディレクトリや任意の場所に一時ファイル（`temp.b64`, `*.json`, `*.diff` 等）を作成してはならない。一時ファイルが必要な処理（コマンドの出力結果の一時保存など）を行う場合は、必ずOS標準の一時ディレクトリ（Windows: `$env:TEMP`、macOS/Linux: `$TMPDIR`）を使用し、処理完了後に確実に出力ファイルを削除すること。
