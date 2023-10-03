cmake_minimum_required(VERSION 3.12)

# Define a single cmake project
project(document-aligner)

enable_testing()

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall")
set(CMAKE_CXX_FLAGS_RELEASE "-Ofast")
set(CMAKE_CXX_FLAGS_DEBUG "-Wextra -g")

# Lazy mode: get me a static binary for at least the essentials
set(Boost_USE_STATIC_LIBS ON)
set(ZLIB_USE_STATIC_LIBS ON)

# Compile all executables into bin/
set(EXECUTABLE_OUTPUT_PATH ${PROJECT_BINARY_DIR}/bin)

if (NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

# We need boost
find_package(Boost 1.41.0 REQUIRED COMPONENTS
  program_options
  unit_test_framework
)

find_package(ICU REQUIRED COMPONENTS
  i18n uc data io
)

# Define where include files live
include_directories(
  ${PROJECT_SOURCE_DIR}
  ${Boost_INCLUDE_DIRS}
  ${ICU_INCLUDE_DIRS}
)

# kpu/preprocess dependency:
if (NOT PREPROCESS_PATH)
    set(PREPROCESS_PATH "${PROJECT_SOURCE_DIR}/preprocess")
endif()

if (NOT SKIP_PREPROCESS_BUILD)
    add_subdirectory(${PREPROCESS_PATH} ${PREPROCESS_PATH}/bin)
endif()

include_directories(${PREPROCESS_PATH})

# find *.h and *.cpp files
file(GLOB dalign_cpp_headers ${CMAKE_CURRENT_SOURCE_DIR}/src/*.h)
file(GLOB dalign_cpp_cpp ${CMAKE_CURRENT_SOURCE_DIR}/src/*.cpp)

# Tool to score alignment between two sets of documents in the same language.
add_executable(docalign docalign.cpp ${dalign_cpp_headers} ${dalign_cpp_cpp})
target_link_libraries(docalign ${Boost_LIBRARIES} preprocess_util)

# Tool to (left) join documents from two sets into a single TSV stream
# Similar to coreutils join, but using line indices and works on gzipped files
add_executable(docjoin docjoin.cpp ${dalign_cpp_headers} ${dalign_cpp_cpp})
target_link_libraries(docjoin preprocess_util)

include(GNUInstallDirs)
install(TARGETS docjoin docalign
    DESTINATION ${CMAKE_INTALL_BINDIR}
    LIBRARY DESTINATION ${CMAKE_LIBRARY_BINDIR}
)

option(COMPILE_TESTS "Compile tests" OFF)
if (COMPILE_TESTS)
  add_subdirectory(tests) 
endif (COMPILE_TESTS)

