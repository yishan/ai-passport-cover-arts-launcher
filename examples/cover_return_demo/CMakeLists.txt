# Minimal play that consumes assets/launcher_contract exactly as an integrated
# play would. CI builds it; the host tests reuse main/play_dispatch.c.
cmake_minimum_required(VERSION 3.16)

set(EXTRA_COMPONENT_DIRS "${CMAKE_CURRENT_LIST_DIR}/../../assets")

include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(cover_return_demo)
