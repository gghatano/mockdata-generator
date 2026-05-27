@AGENTS.md

# Claude Code Notes

Claude Code は `AGENTS.md` を共通指示として扱う。

## Skill location

Claude Code 用の skill discovery path は以下とする。

- `.claude/skills`

このパスは以下を参照する。

- `.agents/skills`

MUST NOT: スキル実体を `.claude/skills` に直接配置しない。  
MUST: スキル実体は `.agents/skills` に配置する。
