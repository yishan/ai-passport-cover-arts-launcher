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
- `references/`：协议细节与验收清单
- `assets/launcher_contract/`：可复用 ESP-IDF 返回组件
- `agents/openai.yaml`：Agent 元数据

## 许可证

MIT License，参见 [`LICENSE`](LICENSE)。
