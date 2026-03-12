# RAGMaker 記述的命名規則ガイドライン (Descriptive Naming Guidelines)

## 1. コンセプト：ファイル名そのものがインデックス
RAGMaker v1.0.0 以降、`catalog.json` は廃止される。LLMがディレクトリ内のファイル名を見ただけで、その内容を 100% 正確に推測できることが、システムの検索精度を決定する。

## 2. 4大カテゴリ構造 (The Big Four Categories)
ドキュメントは、LLMの推論ステップを最適化するため、以下の4つのトップレベルディレクトリのいずれかに分類される。物理階層はこの2階層（Category > File）を原則とする。

1.  **`introduction` (導入)**
    *   プロジェクトの全体像、コンセプト、インストール方法、クイックスタート。
    *   LLMが「最初に何を知るべきか」を把握するためのエントリポイント。
2.  **`reference` (リファレンス)**
    *   API仕様、パラメータ定義、設定項目、コマンドリファレンス。
    *   特定の仕様を「正確に」引くための辞書的データ。
3.  **`guide` (ガイド & サンプル)**
    *   チュートリアル、ハウツー、実装例 (Examples)、ユースケース別の設定例 (Samples)、レシピ、ワークフロー (Workflows)。
    *   「どうやって実現するか」という手順と具体例。
    *   **能動的ドキュメント**はすべてここに分類する。
4.  **`appendix` (付録)**
    *   変更履歴 (Changelog/History)、ライセンス (License)、利用規約 (Terms)、用語集 (Glossary)、一問一答形式のFAQ。
    *   **受動的なメタデータやアーカイブ情報**に限定。
    *   手順（Steps）を含むファイルは `guide` へ、仕様（Spec）を含むファイルは `reference` へ。


## 3. 命名規則のエッセンス

### 3.1. 記述的スネークケース (Descriptive Snake Case)
ファイル名の長さを恐れず、内容を具体的に表現するキーワードをすべて盛り込む。
- **Bad**: `reference/test_api.md`
- **Good**: `reference/vitest_api_test_function_definition_options_and_examples.md`

### 3.2. 階層構造のフラット化 (Prefixing)
深いディレクトリ階層（例: `api/advanced/`）は廃止し、そのコンテクストをファイル名に接頭辞として含める。
- **構成**: `[プロジェクト名]_[カテゴリ]_[詳細内容]_[情報の種類].md`
- **例**: `reference/vitest_config_browser_headless_mode_setup_guide.md`

### 3.3. 技術スタック・対象の明記
対象となる言語、フレームワーク、OSなどを必ず含める。
- **例**: `guide/data_agent_sdk_patterns_python_implementation.md`

## 4. 自動構成の指針
ナレッジベース構築時、LLMはドキュメントの内容を解析し、上記の4カテゴリから最適なものを選択し、記述的なファイル名を生成して物理配置を決定する。
