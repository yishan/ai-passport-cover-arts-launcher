<p align="right">
  <strong>简体中文</strong> · <a href="README.md">English</a>
</p>

# AI Passport Cover Arts Launcher Skill

用于审计或接入 AI Passport 玩法可选 Cover Arts Launcher 返回协议的 Agent Skill。

接入范围保持严格：只有玩法已有的封面／开始页处于活动状态时，长按 Up 约 1.5 秒
才可返回 Cover Arts Launcher。游戏、设置、暂停、结算及其他状态继续保留原有按键
行为。未适配玩法仍然可以安装，并可通过设备重启或重新上电返回 Launcher。

## 安装到当前项目

```bash
npx skills add yishan/ai-passport-cover-arts-launcher --skill ai-passport-cover-arts-launcher -y
```

命令有意不使用 `-g`，在项目目录中执行时按项目级安装。使用前应审阅 Skill；安装
Skill 不代表授权烧录设备、commit、push、发布或创建 Pull Request。

## 直接安装包回退

```bash
npx skills add https://calm.yishan.app/skills/ai-passport-cover-arts-launcher.zip --skill ai-passport-cover-arts-launcher -y
```

也可以直接阅读主指引：
<https://calm.yishan.app/skills/ai-passport-cover-arts-launcher/SKILL.md>。

## 内容

- `SKILL.md` 与 `SKILL.zh_CN.md`：Agent 工作流与安全边界
- `references/`：协议细节、验收清单与接入示例
- `assets/launcher_contract/`：可复用 ESP-IDF 返回组件
- `examples/cover_return_demo/`：基于该组件构建的最小玩法
- `scripts/audit_boot_control.py`：找出玩法及其任何依赖中会破坏“复位返回
  Launcher”的代码
- `tests/host/`：组件与封面门控的主机测试
- `agents/openai.yaml`：Agent 元数据

## 开发

```bash
tests/host/run.sh                   # host tests, needs only a C compiler
scripts/check_i18n_sync.py          # English/Chinese docs structure check
python3 -m unittest discover -s tests/audit     # boot-control audit tests
cd examples/cover_return_demo && idf.py build   # needs ESP-IDF 5.1 or newer
scripts/audit_boot_control.py examples/cover_return_demo --extra assets
```

CI 在每个 Pull Request 上运行以上全部检查，并用多个 ESP-IDF 版本构建示例。

英文文件为权威版本。修改时须在同一变更中同步对应的 `*.zh_CN.md`；同步检查
要求标题结构一致、代码块完全相同、链接目标一致。

## 许可证

MIT License，参见 [`LICENSE`](LICENSE)。
