#!/usr/bin/env lua

-- Run tests for retry logic and event bus client

print("Running retry logic tests...")
print("============================")

-- Run retry manager tests
dofile("test_retry_manager.lua")

print("\n")

-- Run event bus client tests
dofile("test_event_bus_client.lua")

print("\n============================")
print("All retry logic tests completed!")

