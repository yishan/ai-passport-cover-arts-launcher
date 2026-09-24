#ifndef ESP_IMAGE_FORMAT_H
#define ESP_IMAGE_FORMAT_H

#include <stdint.h>

#include "esp_err.h"

typedef enum {
    ESP_IMAGE_VERIFY,
    ESP_IMAGE_VERIFY_SILENT,
} esp_image_load_mode_t;

typedef struct {
    uint32_t offset;
    uint32_t size;
} esp_partition_pos_t;

typedef struct {
    uint32_t start_addr;
    uint32_t image_len;
} esp_image_metadata_t;

esp_err_t esp_image_verify(esp_image_load_mode_t mode,
                           const esp_partition_pos_t *part,
                           esp_image_metadata_t *data);

#endif
