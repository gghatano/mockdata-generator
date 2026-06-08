このディレクトリ (.claude/skills) について
==========================================

このディレクトリは合成データ生成スキルの「接続層」です (Claude Code 用)。
スキル実体はここには置きません。実体の正本は `.agents/skills/` にあります。

セットアップ手順
----------------

このディレクトリを Claude Code のスキル discovery path として機能させるには、
お使いの環境に応じて `.agents/skills` の内容をここに用意してください。

- Linux / macOS (symlink):
    このディレクトリを削除し、`.agents/skills` への symlink を作成します。
      rm -rf .claude/skills
      ln -s ../.agents/skills .claude/skills

- Windows (コピー):
    `.agents/skills/` の各スキルフォルダをこのディレクトリにコピーします。
      Copy-Item -Recurse ..\..\.agents\skills\* .claude\skills\
    コピーした実体は `.gitignore` で除外しているため commit されません。

運用ルール
----------

- スキル実体の編集は必ず `.agents/skills/` 側で行ってください。
- 接続層 (このディレクトリ) には実体を直接置かないでください
  (AGENTS.md の MUST NOT に従う)。
- この README.txt は追跡対象です。コピー / symlink した実体は追跡しません。
