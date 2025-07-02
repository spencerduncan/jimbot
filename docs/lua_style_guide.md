# Comprehensive Lua Style Guide and Best Practices

## Table of Contents
1. [Major Style Guides Overview](#major-style-guides-overview)
2. [Variable Naming Conventions](#variable-naming-conventions)
3. [Table Structures and Metatables](#table-structures-and-metatables)
4. [Module Patterns](#module-patterns)
5. [Error Handling](#error-handling)
6. [Performance Optimization](#performance-optimization)
7. [Memory Management](#memory-management)
8. [Coroutine Patterns](#coroutine-patterns)
9. [Object-Oriented Patterns](#object-oriented-patterns)
10. [Game Modding Conventions](#game-modding-conventions)

## Major Style Guides Overview

### 1. Olivine Labs Lua Style Guide

Key principles:
- **Indentation**: Use soft tabs with 2 spaces
- **Functions**: Prefer many small functions over large ones
- **Variables**: Always use `local` to declare variables
- **Tables**: Use constructor syntax for table creation
- **Strings**: Use single quotes
- **Testing**: Use busted framework in `/spec` folder

### 2. Lua-users Wiki Style Guide

Notable for its acknowledgment of diversity in Lua style:
- **Indentation**: 2 spaces (most common), though 3-4 spaces or tabs also used
- **Comments**: Use space after `--`
- **Flexibility**: "know when to be inconsistent" - readability trumps rules

### 3. Roblox Lua Style Guide

Focused on game development consistency:
- **Naming**: 
  - PascalCase for Roblox APIs
  - camelCase for local variables and functions
  - LOUD_SNAKE_CASE for constants
  - Prefix private members with underscore: `_camelCase`
- **Acronyms**: `aJsonVariable` not `aJSONVariable` (except sets like `anRGBValue`)
- **File Organization**: All `require` calls at top, sorted alphabetically

### 4. Kong Enterprise Patterns

Enterprise-focused conventions:
- Clear directory structure for plugins
- `handler.lua`, `schema.lua`, `daos.lua` pattern
- Performance-focused: avoid blocking functions
- Security-first: validate all external input

## Variable Naming Conventions

### Local vs Global Variables

```lua
-- ALWAYS prefer local variables
local myVariable = 42

-- Global variables only when absolutely necessary
_G.modulename = {}  -- Use _G prefix for clarity

-- Constants
local MAX_RETRIES = 3  -- UPPER_CASE for constants

-- Private members
local _privateData = {}  -- underscore prefix for private

-- Ignored variables
for _, value in pairs(table) do  -- single underscore for ignored
    print(value)
end
```

### Reserved Patterns
- **Avoid**: `_VERSION`, `_LOADED` (underscore + uppercase reserved for Lua)
- **Use**: `_` for dummy variables, `_name` for private members

## Table Structures and Metatables

### Basic Table Patterns

```lua
-- Constructor syntax (preferred)
local person = {
    name = "John",
    age = 30,
    greet = function(self)
        return "Hello, " .. self.name
    end
}

-- Define functions externally (better for large tables)
local Car = {}

function Car:drive()
    return self.model .. " is driving"
end
```

### Metatable Best Practices

```lua
-- Basic metatable pattern
local mt = {
    __index = function(table, key)
        -- Custom lookup logic
    end,
    
    __newindex = function(table, key, value)
        -- Custom assignment logic
    end
}

-- Read-only table pattern
function readOnly(t)
    local proxy = {}
    local mt = {
        __index = t,
        __newindex = function()
            error("Attempt to modify read-only table", 2)
        end
    }
    setmetatable(proxy, mt)
    return proxy
end
```

## Module Patterns

### Modern Module Pattern

```lua
-- mymodule.lua
local M = {}

-- Private functions (not exported)
local function privateHelper()
    -- implementation
end

-- Public functions
function M.publicFunction()
    return privateHelper()
end

function M.anotherFunction()
    -- implementation
end

-- Return the module table
return M
```

### Usage Patterns

```lua
-- Method 1: Direct require
local mymod = require("mymodule")
mymod.publicFunction()

-- Method 2: Extract specific functions
local publicFunction = require("mymodule").publicFunction
publicFunction()

-- Method 3: For singletons/factories
local createInstance = require("factory")
local instance = createInstance()
```

## Error Handling

### pcall (Protected Call)

```lua
local function riskyOperation()
    -- May throw error
end

local success, result = pcall(riskyOperation)
if success then
    print("Result:", result)
else
    print("Error:", result)
end
```

### xpcall (Extended Protected Call)

```lua
local function errorHandler(err)
    -- Log error with stack trace
    print("Error: " .. err)
    print(debug.traceback())
end

local success, result = xpcall(riskyOperation, errorHandler)
```

### Best Practices
- Use pcall/xpcall for I/O operations and external calls
- Always log errors for debugging
- Provide meaningful error messages to users
- Use xpcall when you need detailed error information

## Performance Optimization

### Table Reuse

```lua
-- BAD: Creating new tables in loops
for i = 1, 1000 do
    local t = {x = i, y = i * 2}  -- Creates 1000 tables
end

-- GOOD: Reuse tables
local t = {}
for i = 1, 1000 do
    t.x = i
    t.y = i * 2
    -- Use t
end
```

### Local Variable Optimization

```lua
-- Cache global functions locally
local print = print
local pairs = pairs
local table_insert = table.insert

-- Access local variables faster than globals
local function processData(data)
    local len = #data  -- Cache length
    for i = 1, len do
        -- Process data[i]
    end
end
```

### Memory Pool Pattern

```lua
local ObjectPool = {}
ObjectPool.__index = ObjectPool

function ObjectPool:new(size)
    local pool = {
        objects = {},
        available = {}
    }
    
    for i = 1, size do
        local obj = {}  -- Create object
        pool.objects[i] = obj
        pool.available[i] = obj
    end
    
    return setmetatable(pool, self)
end

function ObjectPool:get()
    return table.remove(self.available)
end

function ObjectPool:release(obj)
    -- Reset object state
    table.insert(self.available, obj)
end
```

## Memory Management

### Garbage Collection Control

```lua
-- Manual garbage collection
collectgarbage("collect")  -- Full collection
collectgarbage("step", 100)  -- Incremental collection

-- Check memory usage
local memUsage = collectgarbage("count")  -- In KB
```

### Weak Tables

```lua
-- Weak reference cache
local cache = {}
setmetatable(cache, {__mode = "v"})  -- Weak values

-- Entries can be garbage collected when not referenced elsewhere
cache[key] = expensiveComputation()
```

## Coroutine Patterns

### Basic Coroutine Usage

```lua
-- Producer-consumer pattern
local function producer()
    for i = 1, 10 do
        coroutine.yield(i)
    end
end

local co = coroutine.create(producer)

-- Consume values
while coroutine.status(co) ~= "dead" do
    local success, value = coroutine.resume(co)
    if success then
        print("Received:", value)
    end
end
```

### Game Development Patterns

```lua
-- Animation timing pattern
local function animateSprite(sprite)
    for i = 1, 10 do
        sprite:setFrame(i)
        waitFrames(5)  -- Yield for 5 frames
    end
end

-- Event-driven pattern
local function gameEvent()
    while true do
        local event = coroutine.yield()
        if event.type == "damage" then
            -- Handle damage
        elseif event.type == "powerup" then
            -- Handle powerup
        end
    end
end
```

## Object-Oriented Patterns

### Basic Class Pattern

```lua
-- Class definition
local Animal = {}
Animal.__index = Animal

function Animal:new(name)
    local instance = {
        name = name
    }
    return setmetatable(instance, self)
end

function Animal:speak()
    return self.name .. " makes a sound"
end
```

### Inheritance Pattern

```lua
-- Base class
local Vehicle = {}
Vehicle.__index = Vehicle

function Vehicle:new(model)
    local instance = {
        model = model
    }
    return setmetatable(instance, self)
end

-- Derived class
local Car = setmetatable({}, {__index = Vehicle})
Car.__index = Car

function Car:new(model, doors)
    local instance = Vehicle.new(self, model)
    instance.doors = doors
    return setmetatable(instance, Car)
end

function Car:honk()
    return self.model .. " goes beep!"
end
```

## Game Modding Conventions

### Balatro/LÖVE2D Specific Patterns

```lua
-- Main entry point
-- main.lua
local Game = {}

function love.load()
    -- Initialize game
end

function love.update(dt)
    -- Update game state
end

function love.draw()
    -- Render game
end
```

### Event-Driven Card Game Patterns

```lua
-- Card event system
local EventSystem = {}
EventSystem.listeners = {}

function EventSystem:on(event, callback)
    self.listeners[event] = self.listeners[event] or {}
    table.insert(self.listeners[event], callback)
end

function EventSystem:emit(event, ...)
    local listeners = self.listeners[event] or {}
    for _, callback in ipairs(listeners) do
        callback(...)
    end
end

-- Usage
EventSystem:on("card_played", function(card)
    -- Handle card play
end)
```

### Mod Structure Best Practices

```lua
-- mod/main.lua
local Mod = {}

-- Use proper namespacing
Mod.config = {
    name = "MyMod",
    version = "1.0.0"
}

-- Hook into game systems properly
function Mod:init()
    -- Register with game systems
end

-- Clean module pattern
return Mod
```

## Summary of Key Best Practices

1. **Always use `local`** - Global variables should be extremely rare
2. **Prefer small functions** - Easier to test and understand
3. **Reuse tables** - Critical for performance in games
4. **Use proper error handling** - pcall/xpcall for robustness
5. **Follow consistent naming** - camelCase for locals, UPPER_CASE for constants
6. **Document your code** - Especially public APIs
7. **Test thoroughly** - Use testing frameworks like busted
8. **Optimize carefully** - Profile before optimizing
9. **Use metatables wisely** - Powerful but can be confusing
10. **Keep modules simple** - One module, one purpose