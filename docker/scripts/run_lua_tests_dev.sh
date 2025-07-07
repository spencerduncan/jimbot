#!/bin/bash
# Development version that runs tests and keeps container alive
/app/run_lua_tests.sh
echo "Tests completed. Container staying alive for debugging..."
echo "Available commands:"
echo "  lua tests/run_tests.lua           - Run shop navigation tests"
echo "  lua tests/run_all_tests.lua       - Run game state tests"
echo "  luacheck tests/                   - Run lint checks"
echo "  stylua --check tests/             - Run style checks"
echo "  busted                            - Run Busted tests"
tail -f /dev/null