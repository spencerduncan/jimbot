# Headless Balatro Implementation Guide

## Overview

This guide provides technical implementation details for creating a headless
version of Balatro that integrates with the JimBot system architecture. The
headless implementation must be completed by Week 2 to support MCP integration
and shares a 2GB memory allocation with the MCP server.

## Integration with JimBot Architecture

The headless Balatro implementation serves as the game engine interface, working
in conjunction with the MCP server to publish game events to the Event Bus. The
architecture follows:

```
Headless Balatro → MCP Server → Event Bus → All Components
```

This design maintains clean separation between game logic and the learning
system while enabling high-frequency event capture.

## Technical foundation and architecture

Balatro runs on the LÖVE 2D v11.5 framework, with approximately 30,000 lines of
Lua code accessible by extracting the executable. The game's modding ecosystem
centers around **Steamodded**, a comprehensive framework that provides APIs for
content creation, and **Lovely Injector**, which enables runtime code
modification without altering the executable. Understanding these systems is
crucial for implementing a headless mod that maintains compatibility with
existing modifications.

The core challenge lies in Love2D's graphics module architecture, which requires
an OpenGL context through the window module. For headless operation, we must
either completely disable these modules or implement comprehensive mocking
strategies that intercept graphics calls while maintaining game logic integrity.

## Implementation approach for headless rendering

### Configuration-based headless mode

The simplest approach leverages Love2D's configuration system to disable
graphics entirely:

```lua
-- conf.lua modification via Lovely patch
function love.conf(t)
    if HEADLESS_MODE then
        t.window = false
        t.modules.graphics = false
        t.modules.window = false
        t.modules.audio = false  -- Optional for server deployment
    end
end
```

However, this approach breaks any code that references `love.graphics.*`
functions, requiring extensive modifications to Balatro's codebase.

### Comprehensive graphics mocking strategy

A more robust solution implements a complete mock of Love2D's graphics API. This
approach maintains compatibility with existing code while bypassing actual
rendering:

```lua
-- headless_graphics_mock.lua
local mock = {}

-- Mock all graphics functions with no-ops
local graphics_functions = {
    'draw', 'print', 'rectangle', 'circle', 'line',
    'setColor', 'clear', 'push', 'pop', 'translate'
}

for _, func in ipairs(graphics_functions) do
    mock[func] = function() end
end

-- Mock resource creation with metadata objects
mock.newImage = function(path)
    return {
        getWidth = function() return 64 end,
        getHeight = function() return 64 end,
        type = "Image",
        path = path
    }
end

-- Canvas mock with ImageData support for state capture
mock.newCanvas = function(width, height)
    local imageData = {}
    for y = 0, height-1 do
        imageData[y] = {}
        for x = 0, width-1 do
            imageData[y][x] = {0, 0, 0, 0}
        end
    end

    return {
        getWidth = function() return width end,
        getHeight = function() return height end,
        renderTo = function(func) if func then func() end end,
        newImageData = function() return imageData end
    }
end
```

### Virtual framebuffer alternative

For maximum compatibility, especially during development, using Xvfb provides a
virtual display:

```bash
#!/bin/bash
# headless_balatro.sh
Xvfb :99 -screen 0 1024x768x24 -ac &
export DISPLAY=:99
love /path/to/balatro --headless-debug
kill $!
```

## Integrating with Balatro's modding architecture

### Steamodded integration

Create a Steamodded-compatible mod structure that initializes headless mode:

```lua
-- Mods/HeadlessBalatro/HeadlessBalatro.lua
SMODS.Mods["HeadlessBalatro"] = {
    mod_id = "HeadlessBalatro",
    name = "Headless Balatro",
    version = "1.0.0",
    author = "YourName",
    description = "Enables headless mode with HTTP debugging"
}

-- Hook into Steamodded initialization
local old_game_load = Game.load
function Game:load(save_data)
    if arg and arg[1] == "--headless" then
        require("headless_graphics_mock")
        love.graphics = mock
        initializeHTTPServer()
    end
    return old_game_load(self, save_data)
end
```

### Lovely Injector patches

Use Lovely's patch system to inject headless functionality:

```toml
# lovely.toml
[manifest]
version = "1.0.0"
priority = 100  # High priority to load early

[[patches]]
[patches.pattern]
target = "main.lua"
pattern = "love.load = function"
position = "before"
payload = '''
-- Check for headless mode
if arg and (arg[1] == "--headless" or os.getenv("BALATRO_HEADLESS")) then
    _G.HEADLESS_MODE = true
    require("Mods/HeadlessBalatro/headless_init")
end
'''

[[patches]]
[patches.module]
source = "Mods/HeadlessBalatro/http_server.lua"
target = "http_server"
```

## HTTP server implementation for game state visualization

### Server architecture using lua-http

The lua-http library provides the most comprehensive solution for non-blocking
HTTP/WebSocket support:

```lua
-- http_server.lua
local http_server = require "http.server"
local websocket = require "http.websocket"
local json = require "cjson"
local cqueues = require "cqueues"

local debug_server = {}

function debug_server:new(port)
    local server = http_server.new {
        host = "127.0.0.1",
        port = port or 8080,
        onstream = function(server, stream)
            self:handle_request(stream)
        end
    }

    -- WebSocket endpoint for real-time updates
    server:add_route("/ws/gamestate", function(stream)
        local ws = websocket.new_from_stream(stream, stream:get_headers())
        if ws then
            self:handle_websocket(ws)
        end
    end)

    return server
end

function debug_server:handle_request(stream)
    local headers = stream:get_headers()
    local path = headers:get(":path")

    -- REST API endpoints
    local routes = {
        ["/api/game/state"] = function()
            return self:get_game_state()
        end,
        ["/api/game/cards"] = function()
            return self:get_card_state()
        end,
        ["/api/game/jokers"] = function()
            return self:get_joker_state()
        end,
        ["/api/debug/eval"] = function(body)
            return self:evaluate_lua(body)
        end
    }

    local handler = routes[path]
    if handler then
        local response = handler(stream:get_body_as_string())
        stream:write_head(200, {
            ["content-type"] = "application/json",
            ["access-control-allow-origin"] = "*"
        })
        stream:write_body(json.encode(response))
    else
        stream:write_head(404)
    end
end

function debug_server:get_game_state()
    -- Extract relevant game state from G.GAME
    return {
        round = G.GAME.round,
        ante = G.GAME.round_resets.ante,
        chips = G.GAME.chips,
        dollars = G.GAME.dollars,
        hands = G.GAME.current_round.hands_left,
        discards = G.GAME.current_round.discards_left,
        deck_size = #G.deck.cards,
        jokers = self:serialize_jokers(),
        timestamp = os.time()
    }
end
```

### WebSocket integration for real-time updates

```lua
function debug_server:handle_websocket(ws)
    -- Subscribe to game events
    local update_queue = {}

    -- Hook into Balatro's update cycle
    local old_update = Game.update
    function Game:update(dt)
        old_update(self, dt)

        -- Capture state changes
        if self.STATE ~= ws.last_state then
            table.insert(update_queue, {
                type = "state_change",
                state = self.STATE,
                data = debug_server:get_game_state()
            })
            ws.last_state = self.STATE
        end
    end

    -- Send updates at controlled rate
    while ws:get_state() == "open" do
        if #update_queue > 0 then
            ws:send(json.encode(update_queue))
            update_queue = {}
        end
        cqueues.sleep(0.1)  -- 10 updates per second
    end
end
```

## Performance optimization strategies

### Memory management in headless mode

Headless operation typically reduces memory usage by 40-60% by eliminating
texture storage and OpenGL buffers. However, careful management is still
required:

```lua
-- Resource pooling for frequently created objects
local card_pool = {}
local MAX_POOL_SIZE = 100

function create_card(config)
    local card = table.remove(card_pool) or {}
    -- Initialize card properties
    return card
end

function destroy_card(card)
    -- Clear card data
    for k in pairs(card) do
        card[k] = nil
    end
    if #card_pool < MAX_POOL_SIZE then
        table.insert(card_pool, card)
    end
end
```

### CPU optimization for server deployment

```lua
-- Adaptive frame rate based on active connections
function adaptive_update()
    local target_fps = 60
    if #active_connections == 0 then
        target_fps = 10  -- Idle mode
    elseif headless_mode then
        target_fps = 30  -- Balance performance/responsiveness
    end

    love.timer.sleep(1/target_fps - love.timer.getDelta())
end
```

## Testing strategies for headless implementation

### Integration with Cute testing framework

```lua
-- test_headless.lua
local cute = require("cute")

-- Test graphics mocking
notion("Graphics calls don't crash in headless mode", function()
    love.graphics.print("Test", 0, 0)
    love.graphics.rectangle("fill", 0, 0, 100, 100)
    check(true).is(true)  -- No crash means success
end)

-- Test game state serialization
notion("Game state serializes correctly", function()
    local state = get_game_state()
    local json_state = json.encode(state)
    local decoded = json.decode(json_state)
    check(decoded.ante).is(state.ante)
end)

-- Run with: love . --cute-headless
```

### Automated CI/CD pipeline

```yaml
# .github/workflows/headless-test.yml
name: Headless Balatro Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Install Love2D
        run: |
          sudo add-apt-repository ppa:bartbes/love-stable
          sudo apt-get update
          sudo apt-get install love

      - name: Install dependencies
        run: |
          sudo apt-get install -y xvfb
          luarocks install http
          luarocks install cjson

      - name: Run headless tests
        run: |
          xvfb-run -a love . --headless --cute-headless

      - name: Performance benchmark
        run: |
          xvfb-run -a love . --headless --benchmark
```

## Security considerations for production deployment

```lua
-- Security middleware
local security = {}

function security:check_request(stream)
    local headers = stream:get_headers()
    local client_ip = headers:get("x-forwarded-for") or
                     stream:get_peer():ip()

    -- IP whitelist for debug interface
    local whitelist = {"127.0.0.1", "::1"}
    if not table.contains(whitelist, client_ip) then
        stream:write_head(403)
        return false
    end

    -- Rate limiting
    if self:is_rate_limited(client_ip) then
        stream:write_head(429)
        return false
    end

    return true
end

-- Disable in production
if _RELEASE_MODE then
    debug_server = nil
    collectgarbage()
end
```

## Browser-based visualization interface

Create a web dashboard for monitoring game state:

```html
<!-- dashboard.html -->
<!DOCTYPE html>
<html>
  <head>
    <title>Balatro Debug Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  </head>
  <body>
    <div id="gameState"></div>
    <canvas id="performanceChart"></canvas>

    <script>
      const ws = new WebSocket('ws://localhost:8080/ws/gamestate');
      const perfChart = new Chart(document.getElementById('performanceChart'), {
        type: 'line',
        data: {
          labels: [],
          datasets: [
            {
              label: 'FPS',
              data: [],
              borderColor: 'rgb(75, 192, 192)',
            },
          ],
        },
        options: {
          scales: {
            y: { beginAtZero: true, max: 60 },
          },
        },
      });

      ws.onmessage = (event) => {
        const updates = JSON.parse(event.data);
        updates.forEach((update) => {
          updateGameStateDisplay(update.data);
          if (update.data.performance) {
            addPerformanceData(update.data.performance);
          }
        });
      };
    </script>
  </body>
</html>
```

## Development Timeline

The headless Balatro implementation follows a parallel track with MCP
development:

### Week 1: Core Headless Implementation

- Implement graphics mocking strategy
- Create Steamodded-compatible mod structure
- Basic game loop without rendering
- Memory usage optimization

### Week 2: MCP Integration

- Implement game state extraction
- Create event publishing interface
- Integrate with MCP server
- Performance testing under load

## Resource Requirements

### Memory Allocation

- Shared 2GB with MCP server
- ~500MB for headless game instance
- ~100MB for HTTP debug server
- Remaining for MCP communication layer

### Development Skills

- Lua programming
- Love2D framework knowledge
- Balatro modding experience
- HTTP server implementation

## Integration Points

### MCP Communication

The headless implementation must expose game state through a local interface
that MCP can efficiently poll or receive callbacks from:

```lua
-- Exposed interface for MCP
_G.HeadlessBalatro = {
    getGameState = function()
        return serialize_game_state(G.GAME)
    end,

    executeAction = function(action)
        return execute_game_action(action)
    end,

    onStateChange = nil  -- Callback set by MCP
}
```

### Performance Requirements

- Game state extraction: <1ms
- Action execution: <5ms
- Memory usage: <600MB per instance
- Support for multiple concurrent games

## Conclusion

Creating a production-ready headless Balatro mod requires careful integration of
Love2D's headless capabilities with Balatro's modding architecture. The
comprehensive graphics mocking approach provides the best balance of
compatibility and performance, while lua-http enables sophisticated debugging
interfaces.

The implementation must be completed by Week 2 to support MCP integration,
sharing a 2GB memory allocation. Key success factors include proper separation
of rendering logic, efficient state serialization, and seamless integration with
the JimBot Event Bus architecture through the MCP server.
