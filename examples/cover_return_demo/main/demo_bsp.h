#ifndef DEMO_BSP_H
#define DEMO_BSP_H

/*
 * Stand-in for a play's BSP input types. A real play already has debounced
 * semantic events like these; reuse them instead of timing GPIOs again.
 */
typedef enum {
    BSP_BTN_UP,
    BSP_BTN_DOWN,
    BSP_BTN_A,
    BSP_BTN_B,
} bsp_btn_t;

typedef enum {
    BSP_BTN_PRESS,
    BSP_BTN_LONG,
} bsp_btn_event_t;

typedef struct {
    bsp_btn_t btn;
    bsp_btn_event_t event;
} bsp_input_t;

#endif
