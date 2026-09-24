<p align="right">
  <strong>简体中文</strong> · <a href="integration-example.md">English</a>
</p>

# 接入示例

本示例把协议接入一个虚构玩法 _Pixel Garden_，展示 Agent 应记录的判断过程，
而不仅是最终 diff。真实玩法中的名称会不同，但判断不应不同。

可构建的最终版本位于
[`examples/cover_return_demo/`](../examples/cover_return_demo/)，
[`tests/host/`](../tests/host/) 在主机上验证其状态门控。

## 起点

```text
pixel-garden/
├── partitions.csv
├── main/
│   ├── CMakeLists.txt
│   ├── app.c          # app_main, input task, state variable
│   └── scenes.c       # title, garden, settings, results
└── components/bsp/    # debounced buttons: press and long events
```

## 1. 修改前检查

```sh
git status --short --branch
grep -rn "LONG" components/bsp main
grep -rn "APP_STATE_" main
grep -n "factory" partitions.csv
idf.py build
python3 "$SKILL_DIR/scripts/audit_boot_control.py" .
```

`$SKILL_DIR` 为本 Skill 的 `SKILL.md` 所在目录。最后一条命令输出：

```text
Boot-control audit: /work/pixel-garden
  BLOCKER: esp_ota_mark_app_valid_cancel_rollback in esp-idf/main/libmain.a(app.c.obj) (linked into pixel_garden.elf)
  BLOCKER: esp_ota_mark_app_valid_cancel_rollback in esp-idf/vendor__cloud_save/libvendor__cloud_save.a(sync.c.obj) (linked into pixel_garden.elf)
  BLOCKER: esp_ota_mark_app_valid_cancel_rollback in pixel-garden/main/app.c (source)
  BLOCKER: esp_ota_mark_app_valid_cancel_rollback in pixel-garden/managed_components/vendor__cloud_save/src/sync.c (source)
    why: confirms the play as valid, so reset and power-cycle keep booting it instead of the Launcher
  NOTE: The play has its own OTA path (esp_ota_begin). While it runs unconfirmed under the Launcher, esp_ota_begin() returns ESP_ERR_OTA_ROLLBACK_INVALID_STATE. Do not "fix" that by marking the play valid; the play's own OTA is outside this protocol and needs a creator decision.
```

Agent 的发现及其含义：

- **输入事件：** BSP 已经提供 `BSP_BTN_LONG`，且
  `CONFIG_BSP_LONG_PRESS_MS=1500`。直接复用，不新增 GPIO 计时。
- **封面状态：** 代码里没有叫 “cover” 的状态。`APP_STATE_TITLE` 就是封面：
  开机后第一个场景，显示玩法主视觉和 “Press A”，结算后也回到这里。按行为
  判断，不按命名判断。
- **为什么必须门控：** 在 `APP_STATE_GARDEN` 中，Up Long 表示给所有植物浇水。
  全局监听会破坏玩法。
- **分发点：** `main/app.c` 中的 `input_task()` 是 BSP 队列的唯一读取者，也是
  `s_state` 的唯一写入者，因此在这里读取状态可靠，无需额外加锁。若有其他任务
  写入状态，判断时必须持有该任务使用的同一把锁。
- **分区：** `partitions.csv` 中有标签为 `factory` 的 app 分区。辅助函数在运行时
  查找它，玩法中不出现任何地址。
- **回滚（玩法自身）：** `app_main()` 调用了从 OTA 示例复制来的
  `esp_ota_mark_app_valid_cancel_rollback()`，它会悄悄破坏“复位返回 Launcher”。
- **回滚（依赖库）：** 为云存档引入的 `vendor__cloud_save` 托管组件在首次同步
  后确认玩法有效。只 grep `main` 永远发现不了它，仅删除 `app.c` 中的调用也修
  不好玩法。链接 map 指出具体库，ELF 证明该调用确实进入固件；对闭源 `.a`
  而言，这是唯一的证据。
- **两者的处理：** 逐条报告 BLOCKER 及其来源。未经创作者同意不做任何修改：
  玩法可能带着自有 OTA 流程单独发布，依赖库可能需要改配置、fork 或替换。
  输出中的 OTA 提示说明了这类代码为何常常出现。

## 2. Diff

把 `assets/launcher_contract/` 原样复制到 `components/launcher_contract/`，然后：

```diff
--- a/main/CMakeLists.txt
+++ b/main/CMakeLists.txt
 idf_component_register(
     SRCS "app.c" "scenes.c"
     INCLUDE_DIRS "."
-    REQUIRES bsp
+    REQUIRES bsp launcher_contract
 )
```

```diff
--- a/main/app.c
+++ b/main/app.c
 #include "bsp_buttons.h"
+#include "esp_err.h"
+#include "esp_log.h"
+#include "launcher_contract.h"
 #include "scenes.h"
 
+static const char *TAG = "app";
+
 static app_state_t s_state = APP_STATE_TITLE;
 
 static void input_task(void *arg)
 {
     bsp_input_t input;
 
     for (;;) {
         if (xQueueReceive(bsp_input_queue(), &input, portMAX_DELAY) != pdTRUE) {
             continue;
         }
+        if (s_state == APP_STATE_TITLE &&
+            input.btn == BSP_BTN_UP &&
+            input.event == BSP_BTN_LONG) {
+            esp_err_t err = launcher_contract_return_to_factory();
+            if (err != ESP_OK) {
+                ESP_LOGE(TAG, "return to Launcher failed: %s", esp_err_to_name(err));
+            }
+            continue;
+        }
         s_state = scene_handle_input(s_state, &input);
     }
 }
```

这就是全部接入：一个复制的组件、一个依赖、一个带门控的分支。没有改动任何
场景、文字或设置。

## 3. 容易犯的错误

```c
/* Wrong: global. Up Long in the garden would leave the play. */
if (input.btn == BSP_BTN_UP && input.event == BSP_BTN_LONG) {
    launcher_contract_return_to_factory();
}

/* Wrong: checks the state after dispatch. Up Long on results, which moves to
 * the title, would immediately leave the play. Gate on the state that
 * received the event. */
s_state = scene_handle_input(s_state, &input);
if (s_state == APP_STATE_TITLE && input.btn == BSP_BTN_UP) { /* ... */ }

/* Wrong: interrupt, timer, or LVGL callback context. The restart can land in
 * the middle of a flash write or while a lock is held. */
static void up_long_cb(lv_event_t *e) { launcher_contract_return_to_factory(); }

/* Wrong: hardcoded address. Partition layouts differ between devices. */
esp_partition_pos_t pos = { .offset = 0x10000, .size = 0x100000 };
```

同样错误的还有：为没有封面的玩法新增封面场景，或添加创作者未要求的屏幕提示。

## 4. 何时应当停止

另一个玩法 _Tiny Racer_ 开机直接进入比赛，没有标题场景。检查结论：除非创作者
决定新增封面，否则无法采用增强返回。不要擅自新增。该玩法仍可通过复位或重新
上电保持兼容，报告中应写明这一点。

## 5. 报告

各类结果分别报告，不得相互替代：

- **Build：** `idf.py build` 在玩法目标芯片上通过，并附上该构建的启动控制
  审计结果。
- **Host tests：** 每个状态的门控测试均通过（参见
  [`tests/host/`](../tests/host/)）。
- **Device tests：** 只填写真机上实际执行过的项目，按
  [验收清单](protocol.zh_CN.md#验收清单) 逐条列出。
- **Unverified：** 其余全部，包括无人执行的复位与重新上电，以及创作者尚未
  决定的所有启动控制 BLOCKER。
