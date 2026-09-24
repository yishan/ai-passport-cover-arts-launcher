#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "freertos/task.h"

#include "esp_log.h"
#include "play_dispatch.h"

static const char *TAG = "demo";

/* Owned by the input task; nothing else writes it. */
static app_state_t s_state = APP_STATE_TITLE;
static QueueHandle_t s_input_queue;

/*
 * The play's existing state machine. Up Long already means "pause" during
 * gameplay, which is exactly the behavior the cover-only gate must preserve.
 */
void game_handle_input(app_state_t state, const bsp_input_t *input)
{
    switch (state) {
    case APP_STATE_TITLE:
        if (input->btn == BSP_BTN_A && input->event == BSP_BTN_PRESS) {
            s_state = APP_STATE_GAME;
        } else if (input->btn == BSP_BTN_B && input->event == BSP_BTN_PRESS) {
            s_state = APP_STATE_SETTINGS;
        }
        break;
    case APP_STATE_GAME:
        if (input->btn == BSP_BTN_UP && input->event == BSP_BTN_LONG) {
            s_state = APP_STATE_PAUSE;
        }
        break;
    case APP_STATE_PAUSE:
    case APP_STATE_SETTINGS:
    case APP_STATE_RESULTS:
        if (input->btn == BSP_BTN_B && input->event == BSP_BTN_PRESS) {
            s_state = APP_STATE_TITLE;
        }
        break;
    }
    ESP_LOGI(TAG, "state %d", (int)s_state);
}

static void input_task(void *arg)
{
    bsp_input_t input;

    (void)arg;
    for (;;) {
        if (xQueueReceive(s_input_queue, &input, portMAX_DELAY) == pdTRUE) {
            play_dispatch_input(s_state, &input);
        }
    }
}

void app_main(void)
{
    /* A real play's BSP posts debounced button events to this queue. */
    s_input_queue = xQueueCreate(8, sizeof(bsp_input_t));
    xTaskCreate(input_task, "input", 4096, NULL, 5, NULL);

    /*
     * Deliberately no esp_ota_mark_app_valid_cancel_rollback(): reset and
     * power-cycle must keep returning to the Launcher.
     */
}
