# Agent Instructions

## 目的

このリポジトリでは、AIエージェント向けの共通資産を `.agents/` 配下に集約する。

`.claude/` や `.codex/` などのツール固有ディレクトリは、`.agents/` を参照するための接続層として扱う。

## 基本方針

- MUST: `.agents/` をAIエージェント向け資産の正本として扱う。
- MUST: スキル実体は `.agents/skills/` に配置する。
- MUST NOT: `.claude/skills/` や `.codex/skills/` にスキル実体を直接配置しない。
- SHOULD: ツール固有ディレクトリには、共通資産と同じ内容を重複配置しない。
- MUST NOT: 業務ワークフローやスキル本文を、明示的な依頼なしに変更しない。

## ディレクトリ構成

- `.agents/skills/`
  - AIエージェントから共通利用するスキルを配置する (実体の正本)。
- `.claude/skills`
  - `.agents/skills` への接続層。説明用の `README.txt` のみを追跡する。
  - Linux/macOS では `.agents/skills` への symlink を作成する。
  - Windows では `.agents/skills` の各スキルを当ディレクトリへコピーする (コピー実体は `.gitignore` で除外)。
  - セットアップ手順は `.claude/skills/README.txt` に記載する。
- `.codex/skills`
  - `.agents/skills` への接続層。説明用の `README.txt` のみを追跡する。
  - Linux/macOS では `.agents/skills` への symlink を作成する。
  - Windows では `.agents/skills` の各スキルを当ディレクトリへコピーする (コピー実体は `.gitignore` で除外)。
  - セットアップ手順は `.codex/skills/README.txt` に記載する。

## 作業時の注意

- 既存の業務ワークフロー、スキル、プロンプトの内容は、明示的な依頼がない限り変更しない。
- ファイル配置や参照構造を変更する場合は、変更前後の構成を確認する。
- symlink が使えない環境では、`.agents/skills` を正本とし、コピー運用の理由と同期方法を明記する。
