#!/usr/bin/env lua
-- Comprehensive test runner that includes all test suites

print("====================================================")
print("     COMPREHENSIVE BALATRO MCP TEST SUITE")
print("====================================================\n")

local test_files = {
    -- Unit tests
    { name = "Action Executor Shop Navigation Tests", file = "tests/unit/test_action_executor_shop_navigation.lua" },
    { name = "Retry Manager Tests", file = "tests/unit/test_retry_manager.lua" },
    { name = "Event Bus Client Tests", file = "tests/unit/test_event_bus_client.lua" },
    
    -- Integration tests
    { name = "Round Eval to Shop Flow Tests", file = "tests/integration/test_round_eval_to_shop_flow.lua" },
    { name = "Retry Integration Tests", file = "tests/integration/test_retry_integration.lua" },
    
    -- Game state tests
    { name = "Game State Extractor Tests", file = "tests/test_game_state_extractor.lua" },
    { name = "Game State Integration Tests", file = "tests/test_game_state_integration.lua" },
}

local total_passed = 0
local total_failed = 0
local suite_results = {}

-- Helper to capture test output
local function capture_test_output(test_file)
    local output = {}
    local original_print = print
    
    -- Override print to capture output
    _G.print = function(...)
        local args = {...}
        local str = table.concat(args, "\t")
        table.insert(output, str)
        original_print(...)
    end
    
    -- Run the test file
    local success, err = pcall(dofile, test_file)
    
    -- Restore original print
    _G.print = original_print
    
    return success, err, output
end

-- Run each test
for _, test in ipairs(test_files) do
    print(string.format("\nRunning: %s", test.name))
    print(string.rep("-", 60))
    
    local success, err, output = capture_test_output(test.file)
    
    if success then
        -- Parse output to find pass/fail counts
        local passed = 0
        local failed = 0
        
        for _, line in ipairs(output) do
            if line:match("✓") then
                passed = passed + 1
            elseif line:match("✗") then
                failed = failed + 1
            elseif line:match("Tests run: (%d+)") then
                -- TestHelper format
                local total = tonumber(line:match("Tests run: (%d+)"))
                local test_passed = tonumber(line:match("Passed: (%d+)")) or 0
                local test_failed = tonumber(line:match("Failed: (%d+)")) or 0
                passed = passed + test_passed
                failed = failed + test_failed
            end
        end
        
        suite_results[test.name] = {
            success = failed == 0,
            passed = passed,
            failed = failed
        }
        
        total_passed = total_passed + passed
        total_failed = total_failed + failed
        
        print(string.format("Result: %d passed, %d failed", passed, failed))
    else
        print(string.format("ERROR: Failed to run test - %s", err))
        suite_results[test.name] = {
            success = false,
            passed = 0,
            failed = 1,
            error = err
        }
        total_failed = total_failed + 1
    end
end

-- Print summary
print("\n\n====================================================")
print("                  FINAL SUMMARY")
print("====================================================\n")

for name, result in pairs(suite_results) do
    local status = result.success and "✓ PASS" or "✗ FAIL"
    print(string.format("%s %s", status, name))
    if result.error then
        print(string.format("    Error: %s", result.error))
    else
        print(string.format("    Passed: %d, Failed: %d", result.passed, result.failed))
    end
end

print(string.format("\n%s", string.rep("-", 60)))
print(string.format("TOTAL: %d passed, %d failed", total_passed, total_failed))
print(string.format("%s\n", string.rep("-", 60)))

-- Exit code
local exit_code = total_failed == 0 and 0 or 1

if total_failed == 0 then
    print("✓ All tests passed!")
else
    print(string.format("✗ %d test(s) failed", total_failed))
end

os.exit(exit_code)