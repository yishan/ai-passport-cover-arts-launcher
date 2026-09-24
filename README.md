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
npx skills add https://calm.yishan.app/skills/ai-passport-cover-arts-launcher.zip --skill ai-passport-cover-arts-launcher -y
```

You can also read the canonical instructions directly at
<https://calm.yishan.app/skills/ai-passport-cover-arts-launcher/SKILL.md>.

## Contents

- `SKILL.md` and `SKILL.zh_CN.md`: Agent workflow and safety boundaries
- `references/`: protocol details, acceptance checks, and a worked integration
  example
- `assets/launcher_contract/`: reusable ESP-IDF return component
- `examples/cover_return_demo/`: minimal play that builds against the component
- `scripts/audit_boot_control.py`: finds code in a play or any of its
  dependencies that would break reset-to-Launcher
- `tests/host/`: host tests for the component and the cover-only gate
- `agents/openai.yaml`: Agent metadata

## Development

```bash
tests/host/run.sh                   # host tests, needs only a C compiler
scripts/check_i18n_sync.py          # English/Chinese docs structure check
python3 -m unittest discover -s tests/audit     # boot-control audit tests
cd examples/cover_return_demo && idf.py build   # needs ESP-IDF 5.1 or newer
scripts/audit_boot_control.py examples/cover_return_demo --extra assets
```

CI runs all of these on every pull request, building the example with several
ESP-IDF releases.

English files are canonical. Update the matching `*.zh_CN.md` file in the same
change; the sync check requires the same headings, identical code blocks, and
the same link targets.

## License

MIT License. See [`LICENSE`](LICENSE).
