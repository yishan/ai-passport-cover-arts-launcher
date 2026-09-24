#ifndef ESP_LOG_H
#define ESP_LOG_H

void stub_log(char level, const char *tag, const char *format, ...)
    __attribute__((format(printf, 3, 4)));

#define ESP_LOGE(tag, ...) stub_log('E', tag, __VA_ARGS__)
#define ESP_LOGW(tag, ...) stub_log('W', tag, __VA_ARGS__)
#define ESP_LOGI(tag, ...) stub_log('I', tag, __VA_ARGS__)

#endif
