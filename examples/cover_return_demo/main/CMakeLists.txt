idf_component_register(
    SRCS "main.c" "play_dispatch.c"
    INCLUDE_DIRS "."
    REQUIRES launcher_contract log
)
