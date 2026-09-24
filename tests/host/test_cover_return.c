/*
 * Host tests for assets/launcher_contract and the reference dispatcher in
 * examples/cover_return_demo. ESP-IDF calls are replaced by the stubs below;
 * esp_restart() longjmps back into the test so "the device rebooted" is
 * observable.
 */
#include <setjmp.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>

#include "esp_image_format.h"
#include "esp_ota_ops.h"
#include "esp_partition.h"
#include "esp_system.h"
#include "launcher_contract.h"
#include "play_dispatch.h"

static const esp_partition_t s_factory = {
    ESP_PARTITION_TYPE_APP, ESP_PARTITION_SUBTYPE_APP_FACTORY,
    0x20000, 0x100000, "factory",
};
static const esp_partition_t s_ota0 = {
    ESP_PARTITION_TYPE_APP, ESP_PARTITION_SUBTYPE_APP_OTA_0,
    0x120000, 0x100000, "ota_0",
};

static struct {
    const esp_partition_t *factory;
    const esp_partition_t *running;
    esp_err_t verify_result;
    esp_err_t set_boot_result;

    int verify_calls;
    esp_partition_pos_t verify_pos;
    esp_image_load_mode_t verify_mode;
    const esp_partition_t *boot_partition;
    int restarts;
    int error_logs;
    int game_calls;
} s;

static jmp_buf s_restart_jump;
static int s_failures;

const char *esp_err_to_name(esp_err_t code)
{
    static char name[32];
    snprintf(name, sizeof(name), "0x%x", (unsigned)code);
    return name;
}

const esp_partition_t *esp_partition_find_first(esp_partition_type_t type,
                                                esp_partition_subtype_t subtype,
                                                const char *label)
{
    if (type != ESP_PARTITION_TYPE_APP ||
        subtype != ESP_PARTITION_SUBTYPE_APP_FACTORY ||
        label == NULL || strcmp(label, "factory") != 0) {
        return NULL;
    }
    return s.factory;
}

const esp_partition_t *esp_ota_get_running_partition(void)
{
    return s.running;
}

esp_err_t esp_image_verify(esp_image_load_mode_t mode,
                           const esp_partition_pos_t *part,
                           esp_image_metadata_t *data)
{
    (void)data;
    s.verify_calls++;
    s.verify_mode = mode;
    s.verify_pos = *part;
    return s.verify_result;
}

esp_err_t esp_ota_set_boot_partition(const esp_partition_t *partition)
{
    if (s.set_boot_result == ESP_OK) {
        s.boot_partition = partition;
    }
    return s.set_boot_result;
}

void esp_restart(void)
{
    s.restarts++;
    longjmp(s_restart_jump, 1);
}

void stub_log(char level, const char *tag, const char *format, ...)
{
    va_list args;

    if (level == 'E') {
        s.error_logs++;
    }
    fprintf(stderr, "    [%c %s] ", level, tag);
    va_start(args, format);
    vfprintf(stderr, format, args);
    va_end(args);
    fputc('\n', stderr);
}

void game_handle_input(app_state_t state, const bsp_input_t *input)
{
    (void)state;
    (void)input;
    s.game_calls++;
}

#define CHECK(cond)                                                     \
    do {                                                                \
        if (!(cond)) {                                                  \
            fprintf(stderr, "  FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); \
            s_failures++;                                               \
        }                                                               \
    } while (0)

static void reset_device(void)
{
    memset(&s, 0, sizeof(s));
    s.factory = &s_factory;
    s.running = &s_ota0;
    s.verify_result = ESP_OK;
    s.set_boot_result = ESP_OK;
}

/* Returns the helper's error, or ESP_OK when it restarted the device. */
static esp_err_t call_helper(void)
{
    if (setjmp(s_restart_jump) != 0) {
        return ESP_OK;
    }
    return launcher_contract_return_to_factory();
}

static void dispatch(app_state_t state, bsp_btn_t btn, bsp_btn_event_t event)
{
    bsp_input_t input = { btn, event };

    if (setjmp(s_restart_jump) != 0) {
        return;
    }
    play_dispatch_input(state, &input);
}

static void test_helper_restarts_into_verified_factory(void)
{
    reset_device();
    CHECK(call_helper() == ESP_OK);
    CHECK(s.restarts == 1);
    CHECK(s.boot_partition == &s_factory);
    CHECK(s.verify_calls == 1);
    CHECK(s.verify_mode == ESP_IMAGE_VERIFY);
    /* Verification uses the discovered partition, not a hardcoded address. */
    CHECK(s.verify_pos.offset == s_factory.address);
    CHECK(s.verify_pos.size == s_factory.size);
    CHECK(s.error_logs == 0);
}

static void test_helper_missing_factory(void)
{
    reset_device();
    s.factory = NULL;
    CHECK(call_helper() == ESP_ERR_NOT_FOUND);
    CHECK(s.restarts == 0);
    CHECK(s.boot_partition == NULL);
    CHECK(s.error_logs == 1);
}

static void test_helper_already_running_factory(void)
{
    reset_device();
    s.running = &s_factory;
    CHECK(call_helper() == ESP_ERR_INVALID_STATE);
    CHECK(s.restarts == 0);
    CHECK(s.verify_calls == 0);
    CHECK(s.boot_partition == NULL);
    CHECK(s.error_logs == 1);
}

static void test_helper_invalid_factory_image(void)
{
    reset_device();
    s.verify_result = ESP_ERR_IMAGE_INVALID;
    CHECK(call_helper() == ESP_ERR_OTA_VALIDATE_FAILED);
    CHECK(s.restarts == 0);
    CHECK(s.boot_partition == NULL);
    CHECK(s.error_logs == 1);
}

static void test_helper_set_boot_failure(void)
{
    reset_device();
    s.set_boot_result = ESP_FAIL;
    CHECK(call_helper() == ESP_FAIL);
    CHECK(s.restarts == 0);
    CHECK(s.error_logs == 1);
}

static void test_dispatch_cover_up_long_returns(void)
{
    reset_device();
    dispatch(APP_STATE_TITLE, BSP_BTN_UP, BSP_BTN_LONG);
    CHECK(s.restarts == 1);
    CHECK(s.boot_partition == &s_factory);
    CHECK(s.game_calls == 0);
}

static void test_dispatch_other_states_keep_up_long(void)
{
    static const app_state_t states[] = {
        APP_STATE_GAME, APP_STATE_PAUSE, APP_STATE_SETTINGS, APP_STATE_RESULTS,
    };
    size_t i;

    for (i = 0; i < sizeof(states) / sizeof(states[0]); i++) {
        reset_device();
        dispatch(states[i], BSP_BTN_UP, BSP_BTN_LONG);
        CHECK(s.restarts == 0);
        CHECK(s.verify_calls == 0);
        CHECK(s.game_calls == 1);
    }
}

static void test_dispatch_cover_other_inputs_pass_through(void)
{
    reset_device();
    dispatch(APP_STATE_TITLE, BSP_BTN_UP, BSP_BTN_PRESS);
    dispatch(APP_STATE_TITLE, BSP_BTN_DOWN, BSP_BTN_LONG);
    dispatch(APP_STATE_TITLE, BSP_BTN_A, BSP_BTN_PRESS);
    CHECK(s.restarts == 0);
    CHECK(s.verify_calls == 0);
    CHECK(s.game_calls == 3);
}

static void test_dispatch_failure_keeps_play_running(void)
{
    reset_device();
    s.factory = NULL;
    dispatch(APP_STATE_TITLE, BSP_BTN_UP, BSP_BTN_LONG);
    CHECK(s.restarts == 0);
    /* Helper and dispatcher each log; the event is consumed, not replayed. */
    CHECK(s.error_logs == 2);
    CHECK(s.game_calls == 0);
}

int main(void)
{
    static const struct {
        const char *name;
        void (*run)(void);
    } tests[] = {
        { "helper restarts into verified factory", test_helper_restarts_into_verified_factory },
        { "helper: missing factory", test_helper_missing_factory },
        { "helper: already running factory", test_helper_already_running_factory },
        { "helper: invalid factory image", test_helper_invalid_factory_image },
        { "helper: set boot partition fails", test_helper_set_boot_failure },
        { "dispatch: cover + Up Long returns", test_dispatch_cover_up_long_returns },
        { "dispatch: other states keep Up Long", test_dispatch_other_states_keep_up_long },
        { "dispatch: other cover inputs pass through", test_dispatch_cover_other_inputs_pass_through },
        { "dispatch: failure keeps play running", test_dispatch_failure_keeps_play_running },
    };
    size_t i;

    for (i = 0; i < sizeof(tests) / sizeof(tests[0]); i++) {
        int before = s_failures;

        fprintf(stderr, "%s\n", tests[i].name);
        tests[i].run();
        fprintf(stderr, "  %s\n", s_failures == before ? "ok" : "FAILED");
    }
    if (s_failures != 0) {
        fprintf(stderr, "%d check(s) failed\n", s_failures);
        return 1;
    }
    fprintf(stderr, "all host tests passed\n");
    return 0;
}
