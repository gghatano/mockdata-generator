# GitHub Copilot Instructions

このリポジトリの共通AIエージェント指示は `AGENTS.md` を正本とする。

- AIエージェント向け共通資産は `.agents/` 配下を正本として扱う。
- スキル実体は `.agents/skills/` に配置する。
- `.claude/skills` や `.codex/skills` は `.agents/skills` への接続層として扱い、説明用の `README.txt` のみを追跡する。
  - Linux/macOS では `.agents/skills` への symlink を作成する。
  - Windows では `.agents/skills` の各スキルを接続層へコピーする (コピー実体は `.gitignore` で除外)。
  - 接続層に実体を直接置かない (各ディレクトリの `README.txt` 参照)。
- 業務ワークフローやスキル本文は、明示的な依頼なしに変更しない。
