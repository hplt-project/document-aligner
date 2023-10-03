add_executable(ngram_test ngram_test.cpp ${dalign_cpp_headers} ${dalign_cpp_cpp})
target_link_libraries(ngram_test ${Boost_UNIT_TEST_FRAMEWORK_LIBRARY} preprocess_util)
add_test(NAME ngram_test COMMAND ngram_test)