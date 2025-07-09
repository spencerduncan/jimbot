#!/usr/bin/env lua
-- Test runner for BalatroMCP tests
-- Runs all test suites and provides summary

local test_suites = {
    "tests/unit/test_action_executor_shop_navigation.lua",
    "tests/unit/test_retry_manager.lua",
    "tests/unit/test_event_bus_client.lua",
    "tests/integration/test_round_eval_to_shop_flow.lua",
    "tests/integration/test_retry_integration.lua",
}

print("========================================")
print("BalatroMCP Test Suite Runner")
print("========================================")
print(string.format("Running %d test suites...\n", #test_suites))

local total_passed = 0
local total_failed = 0
local suite_results = {}

for i, suite in ipairs(test_suites) do
    print(string.format("\n[Suite %d/%d] %s", i, #test_suites, suite))

    -- Run the test suite in a protected environment
    local success, result = pcall(function()
        -- Reset global state for each suite
        package.loaded["tests.test_helper"] = nil

        -- Execute the suite
        dofile(suite)

        -- Get results from TestHelper
        local TestHelper = require("tests.test_helper")
        return {
            passed = TestHelper.passed,
            failed = TestHelper.failed,
            total = TestHelper.passed + TestHelper.failed,
        }
    end)

    if success then
        table.insert(suite_results, {
            name = suite,
            passed = result.passed,
            failed = result.failed,
            total = result.total,
            success = true,
        })
        total_passed = total_passed + result.passed
        total_failed = total_failed + result.failed
    else
        print(string.format("ERROR: Failed to run suite: %s", tostring(result)))
        table.insert(suite_results, {
            name = suite,
            passed = 0,
            failed = 1,
            total = 1,
            success = false,
            error = result,
        })
        total_failed = total_failed + 1
    end
end

-- Print final summary
print("\n\n========================================")
print("FINAL TEST SUMMARY")
print("========================================")

for _, suite in ipairs(suite_results) do
    local status = suite.success and (suite.failed == 0 and "PASS" or "FAIL") or "ERROR"
    local color = status == "PASS" and "\27[32m" or "\27[31m"
    local reset = "\27[0m"

    print(
        string.format(
            "%s[%s]%s %s - %d/%d tests passed",
            color,
            status,
            reset,
            suite.name,
            suite.passed,
            suite.total
        )
    )

    if suite.error then
        print(string.format("  Error: %s", suite.error))
    end
end

print(
    string.format(
        "\nTotal: %d passed, %d failed out of %d tests",
        total_passed,
        total_failed,
        total_passed + total_failed
    )
)

-- Exit with appropriate code
local exit_code = total_failed == 0 and 0 or 1
print(string.format("\nExiting with code: %d", exit_code))

if exit_code ~= 0 then
    print("\nTests failed! Please fix the failing tests before committing.")
else
    print("\nAll tests passed! ✓")
end

os.exit(exit_code)
