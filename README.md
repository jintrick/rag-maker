# RAGMaker (v0.9.1)

Web/GitHub/Localソースから RAG 用ナレッジベース（KB）を構築する、AI エージェント向けの対話型ツールスイート。

## 🛠 コマンド

### 1. `/rag <Source_URI>` (KB構築)
AI エージェントが以下の原子的な工程を遂行し、ナレッジベースを自動生成する。

- **初期化**: `.tmp/cache/` ディレクトリの作成。
- **データ取得**: `http_fetch` / `github_fetch` / `file_sync` による Markdown 抽出。
- **AI Piloting**: ボット検知や JS サイトに対し、Playwright 経由で `browser_navigate` / `browser_extract` を実行。
- **メタデータ登録**: AI 推論による `title` / `summary` の生成と `catalog.json` への記録。

### 2. `/ask <Question>` (QA)
ナレッジベースのルートで実行し、`catalog.json` のメタデータを参照して根拠に基づいた回答を生成する。

## 🚀 クイックスタート

```bash
# インストール
pip install -e .
playwright install chromium

# 実行例
gemini /rag "https://example.com/docs"
```

## 🏗 アーキテクチャ

- **マスターカタログ (`discovery.json`)**: プロジェクト全ツールの「定義書」。エージェントの行動原理となる。
- **ドキュメントカタログ (`catalog.json`)**: 各 KB の「目録」。相対パス管理によりポータビリティを確保。
- **排他制御 (`LockedJsonWriter`)**: OS レベル의ファイルロックにより、同時書き込み時のデータ破損を防止。

## ⚠️ 依存関係
- Python 3.8+
- Node.js (`readability-cli` 必須)
- Playwright (Chromium)
