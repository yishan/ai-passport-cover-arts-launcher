#ifndef LAUNCHER_CONTRACT_H
#define LAUNCHER_CONTRACT_H

#include "esp_err.h"

/**
 * Reverify the factory Launcher, select it as the boot target, and restart.
 *
 * The function returns only on failure. It never selects an unverified image.
 * Call it only from task context after the play confirms it is on its cover.
 *
 * Each failure is logged under the "launcher_contract" tag before returning:
 * - ESP_ERR_NOT_FOUND: no app partition labeled "factory".
 * - ESP_ERR_INVALID_STATE: the factory image is the running application.
 * - ESP_ERR_OTA_VALIDATE_FAILED: the factory image failed verification.
 * - Any esp_ota_set_boot_partition() error: the boot target is unchanged.
 */
esp_err_t launcher_contract_return_to_factory(void);

#endif
