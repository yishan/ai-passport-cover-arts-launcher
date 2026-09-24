#ifndef PLAY_DISPATCH_H
#define PLAY_DISPATCH_H

#include "demo_bsp.h"

typedef enum {
    APP_STATE_TITLE, /* the play's existing cover/start page */
    APP_STATE_GAME,
    APP_STATE_PAUSE,
    APP_STATE_SETTINGS,
    APP_STATE_RESULTS,
} app_state_t;

/* The play's existing input handling; unchanged by the integration. */
void game_handle_input(app_state_t state, const bsp_input_t *input);

/* Single input-dispatch point, called from the input task only. */
void play_dispatch_input(app_state_t state, const bsp_input_t *input);

#endif
