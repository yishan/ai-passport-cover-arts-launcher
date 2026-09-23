<p align="right">
  <a href="README.zh_CN.md">简体中文</a> · <strong>English</strong>
</p>

# AI Passport Cover Arts Launcher Skill

An Agent Skill for auditing or integrating the optional Cover Arts Launcher
return protocol into an AI Passport play.

The integration is intentionally narrow: holding Up for about 1.5 seconds may
return to Cover Arts Launcher only while the play's existing cover or start page
is active. Gameplay, settings, pause, results, and other states keep their
existing input behavior. Unadapted plays remain installable and can return to
the Launcher after a device restart or power cycle.

## Install in the current project

```bash
npx skills add yishan/ai-passport-cover-arts-launcher --skill ai-passport-cover-arts-launcher -y
```

This command intentionally omits `-g`, so the Skill is installed at project
scope when run inside a project. Review the Skill before using it; installation
does not authorize flashing hardware, committing, pushing, publishing, or
opening a pull request.

## Direct package fallback

```bash
npx skills add https://cover-arts-launcher.yishan.app/skills/ai-passport-cover-arts-launcher.zip --skill ai-passport-cover-arts-launcher -y
```

You can also read the canonical instructions directly at
<https://cover-arts-launcher.yishan.app/skills/ai-passport-cover-arts-launcher/SKILL.md>.

## Contents

- `SKILL.md` and `SKILL.zh_CN.md`: Agent workflow and safety boundaries
- `references/`: protocol details and acceptance checks
- `assets/launcher_contract/`: reusable ESP-IDF return component
- `agents/openai.yaml`: Agent metadata

## License

MIT License. See [`LICENSE`](LICENSE).
