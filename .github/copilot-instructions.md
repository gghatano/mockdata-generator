# GitHub Copilot Instructions

このリポジトリの共通AIエージェント指示は `AGENTS.md` を正本とする。

- AIエージェント向け共通資産は `.agents/` 配下を正本として扱う。
- スキル実体は `.agents/skills/` に配置する。
- `.claude/skills` や `.codex/skills` は `.agents/skills` への接続層として扱う。
- 業務ワークフローやスキル本文は、明示的な依頼なしに変更しない。
