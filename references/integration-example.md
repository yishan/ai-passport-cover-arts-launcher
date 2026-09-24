<p align="right">
  <a href="integration-example.zh_CN.md">简体中文</a> · <strong>English</strong>
</p>

# Worked integration example

This walkthrough integrates the protocol into a fictional play, _Pixel Garden_.
It shows the reasoning an agent should record, not only the final diff. Names
will differ in real plays; the decisions should not.

A buildable version of the result lives in
[`examples/cover_return_demo/`](../examples/cover_return_demo/), and
[`tests/host/`](../tests/host/) exercises its state gate on a host machine.

## Starting point

```text
pixel-garden/
├── partitions.csv
├── main/
│   ├── CMakeLists.txt
│   ├── app.c          # app_main, input task, state variable
│   └── scenes.c       # title, garden, settings, results
└── components/bsp/    # debounced buttons: press and long events
```

## 1. Inspect before editing

```sh
git status --short --branch
grep -rn "LONG" components/bsp main
grep -rn "APP_STATE_" main
grep -rn "mark_app_valid" main components managed_components
grep -n "factory" partitions.csv
```

What the agent finds, and what each finding means:

- **Input event:** the BSP already emits `BSP_BTN_LONG`, with
  `CONFIG_BSP_LONG_PRESS_MS=1500`. Reuse it; do not add GPIO timing.
- **Cover state:** there is no state called "cover". `APP_STATE_TITLE` is the
  cover: it is the first scene after boot, it shows the play's art with
  "Press A", and results return to it. Match on behavior, not on the word.
- **Why the gate matters:** in `APP_STATE_GARDEN`, Up Long waters every plant.
  A global listener would break gameplay.
- **Dispatch point:** `input_task()` in `main/app.c` is the only reader of the
  BSP queue, and it is the only writer of `s_state`. The state is therefore
  reliable at that point without extra locking. If another task wrote the
  state, the check would have to read it under the lock that task uses.
- **Partitions:** `partitions.csv` has an app partition labeled `factory`. The
  helper finds it at runtime; no address appears in the play.
- **Rollback:** `app_main()` calls `esp_ota_mark_app_valid_cancel_rollback()`,
  copied from an OTA sample. That silently breaks reset-to-Launcher. Report it.
  Remove it only with the creator's agreement, because they may ship the play
  standalone with its own OTA flow.

## 2. The diff

Copy `assets/launcher_contract/` unchanged to `components/launcher_contract/`,
then:

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

That is the whole integration: one copied component, one dependency, and one
guarded branch. No scene, text, or setting changed.

## 3. Tempting mistakes

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

Also wrong: adding a cover scene to a play that has none, or adding an on-screen
hint the creator did not ask for.

## 4. When to stop instead

Another play, _Tiny Racer_, boots straight into a race and has no title scene.
Audit result: the play cannot adopt the enhanced return without a creator
decision to add a cover. Do not add one. The play remains compatible through
reset or power-cycle, and the report should say so.

## 5. Report

Report each category separately and never promote one into another:

- **Build:** `idf.py build` passes for the play's target.
- **Host tests:** the state-gate tests pass for every state (see
  [`tests/host/`](../tests/host/)).
- **Device tests:** fill in only what was run on hardware, one line per item
  from the [acceptance checklist](protocol.md#acceptance-checklist).
- **Unverified:** everything else, including reset and power-cycle if nobody
  ran them, and the `mark_app_valid` finding while the creator has not decided.
