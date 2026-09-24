#include "play_dispatch.h"

#include "esp_err.h"
#include "esp_log.h"
#include "launcher_contract.h"

static const char *TAG = "play";

void play_dispatch_input(app_state_t state, const bsp_input_t *input)
{
    if (state == APP_STATE_TITLE &&
        input->btn == BSP_BTN_UP &&
        input->event == BSP_BTN_LONG) {
        esp_err_t err = launcher_contract_return_to_factory();
        if (err != ESP_OK) {
            ESP_LOGE(TAG, "return to Launcher failed: %s", esp_err_to_name(err));
        }
        return;
    }

    game_handle_input(state, input);
}
