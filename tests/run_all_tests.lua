#!/usr/bin/env lua
-- Master test runner for all game state extractor tests

local test_suites = {
    {
        name = "Unit Tests",
        file = "tests/test_game_state_extractor.lua",
    },
    {
        name = "Integration Tests",
        file = "tests/test_game_state_integration.lua",
    },
}

local total_passed = 0
local total_failed = 0
local suite_results = {}

print("====================================================")
print("     GAME STATE EXTRACTOR TEST SUITE RUNNER")
print("====================================================\n")

-- Run each test suite
for _, suite in ipairs(test_suites) do
    print(string.format("Running %s...", suite.name))
    print(string.rep("-", 50))

    -- Clear any previous module loads
    package.loaded[suite.file:gsub("%.lua$", ""):gsub("/", ".")] = nil

    -- Load and run the test suite
    local success, test_module = pcall(require, suite.file:gsub("%.lua$", ""):gsub("/", "."))

    if success and test_module and test_module.run_all_tests then
        local test_success = test_module.run_all_tests()

        -- Extract results (assuming test modules set these)
        local passed = _G.tests_passed or 0
        local failed = _G.tests_failed or 0

        suite_results[suite.name] = {
            passed = passed,
            failed = failed,
            success = test_success,
        }

        total_passed = total_passed + passed
        total_failed = total_failed + failed

        -- Reset globals
        _G.tests_passed = nil
        _G.tests_failed = nil
    else
        print(string.format("ERROR: Could not load test suite: %s", suite.file))
        suite_results[suite.name] = {
            passed = 0,
            failed = 1,
            success = false,
            error = "Failed to load test suite",
        }
        total_failed = total_failed + 1
    end

    print("")
end

-- Print summary
print("\n====================================================")
print("                  TEST SUMMARY")
print("====================================================\n")

for suite_name, results in pairs(suite_results) do
    local status = results.success and "PASSED" or "FAILED"
    local status_color = results.success and "" or "**"
    print(string.format("%s%s: %s%s", status_color, suite_name, status, status_color))
    print(string.format("  - Passed: %d", results.passed))
    print(string.format("  - Failed: %d", results.failed))
    if results.error then
        print(string.format("  - Error: %s", results.error))
    end
    print("")
end

print(string.rep("-", 50))
print(string.format("TOTAL: %d passed, %d failed", total_passed, total_failed))
print(string.rep("-", 50))

-- Exit with appropriate code
local exit_code = total_failed == 0 and 0 or 1
print(string.format("\nExiting with code: %d", exit_code))

if total_failed == 0 then
    print("\n✓ All tests passed! The game state extractor is working correctly.")
else
    print(string.format("\n✗ %d test(s) failed. Please review the failures above.", total_failed))
end

os.exit(exit_code)
