@AGENTS.md

# Claude Code Notes

Claude Code は `AGENTS.md` を共通指示として扱う。

## Skill location

Claude Code 用の skill discovery path は以下とする。

- `.claude/skills`

このパスは `.agents/skills` を参照するための接続層であり、説明用の `README.txt` のみを追跡する。
環境に応じて以下のいずれかで実体を用意する (詳細は `.claude/skills/README.txt`)。

- Linux/macOS: `.agents/skills` への symlink を作成する。
- Windows: `.agents/skills` の各スキルを `.claude/skills` へコピーする (コピー実体は `.gitignore` で除外)。

MUST NOT: スキル実体を `.claude/skills` に直接配置しない (commit しない)。  
MUST: スキル実体は `.agents/skills` に配置する。
