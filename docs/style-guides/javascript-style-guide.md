# JavaScript Style Guide

This style guide provides comprehensive conventions for JavaScript development in the JimBot project, with a focus on real-time communication, event handling, and mod development patterns.

## Table of Contents

1. [Core Language Features](#core-language-features)
2. [Module Organization](#module-organization)
3. [Async/Await Patterns](#asyncawait-patterns)
4. [WebSocket Programming](#websocket-programming)
5. [Event-Driven Architecture](#event-driven-architecture)
6. [Error Handling](#error-handling)
7. [Testing Conventions](#testing-conventions)

## Core Language Features

### Variable Declarations

```javascript
// ✅ Good - Use const for values that won't be reassigned
const MAX_RETRIES = 3;
const eventEmitter = new EventEmitter();

// ✅ Good - Use let for values that will be reassigned
let currentState = 'idle';
let retryCount = 0;

// ❌ Bad - Never use var
var oldVariable = 'deprecated';
```

### Functions

```javascript
// ✅ Good - Arrow functions for callbacks and short functions
const handleEvent = (event) => {
  console.log('Event received:', event.type);
};

// ✅ Good - Arrow function with implicit return
const calculateScore = (base, multiplier) => base * multiplier;

// ✅ Good - Regular function for methods and complex logic
async function processGameState(state) {
  const validation = validateState(state);
  if (!validation.isValid) {
    throw new ValidationError(validation.errors);
  }
  return await applyStateTransform(state);
}

// ✅ Good - Function expressions for module exports
const gameEventHandler = async function(event) {
  // Complex logic here
};
```

### String Formatting

```javascript
// ✅ Good - Use template literals for interpolation
const message = `Player ${playerName} scored ${points} points`;

// ✅ Good - Use single quotes for simple strings
const eventType = 'game:state:update';

// ✅ Good - Use double quotes to avoid escaping
const jsonString = '{"name": "JimBot", "version": "1.0.0"}';

// ❌ Bad - Avoid string concatenation
const badMessage = 'Player ' + playerName + ' scored ' + points;
```

### Object and Array Operations

```javascript
// ✅ Good - Use destructuring
const { playerId, score, jokers } = gameState;
const [firstJoker, ...remainingJokers] = jokerArray;

// ✅ Good - Use spread operator
const updatedState = { ...previousState, score: newScore };
const allJokers = [...baseJokers, ...modifiedJokers];

// ✅ Good - Use array methods for transformations
const activeJokers = jokers
  .filter(joker => joker.isActive)
  .map(joker => ({
    ...joker,
    multiplier: calculateMultiplier(joker)
  }));

// ❌ Bad - Avoid for-in loops
for (const key in object) { } // Use Object.keys/values/entries instead
```

## Module Organization

### ES Modules (Preferred for New Code)

```javascript
// ✅ Good - Named exports for utilities
export const EVENT_TYPES = {
  GAME_START: 'game:start',
  GAME_END: 'game:end',
  STATE_UPDATE: 'state:update'
};

export function createEventHandler(options) {
  return new EventHandler(options);
}

// ✅ Good - Default export for main class
export default class GameClient {
  constructor(config) {
    this.config = config;
  }
}

// ✅ Good - Import syntax
import GameClient from './GameClient.js';
import { EVENT_TYPES, createEventHandler } from './utils/events.js';
```

### CommonJS (For Node.js Compatibility)

```javascript
// For backwards compatibility when needed
const EventEmitter = require('events');

class GameEventEmitter extends EventEmitter {
  // Implementation
}

module.exports = GameEventEmitter;
module.exports.EVENT_TYPES = EVENT_TYPES;
```

### File Organization

```
src/
├── index.js              # Entry point
├── config/               # Configuration files
│   └── default.js
├── core/                 # Core business logic
│   ├── GameEngine.js
│   └── StateManager.js
├── events/               # Event handling
│   ├── EventBus.js
│   └── handlers/
├── websocket/            # WebSocket communication
│   ├── Client.js
│   └── MessageHandler.js
├── utils/                # Utility functions
│   └── helpers.js
└── types/                # Type definitions (JSDoc)
    └── index.js
```

## Async/Await Patterns

### Basic Async/Await

```javascript
// ✅ Good - Clean async/await with error handling
async function connectToGame(url) {
  try {
    const connection = await establishWebSocketConnection(url);
    const gameState = await connection.getInitialState();
    return { connection, gameState };
  } catch (error) {
    console.error('Failed to connect:', error);
    throw new ConnectionError('Unable to establish game connection', { cause: error });
  }
}

// ✅ Good - Sequential operations when order matters
async function saveGameSequence(state) {
  const validated = await validateGameState(state);
  const processed = await processState(validated);
  const saved = await persistToDatabase(processed);
  return saved;
}
```

### Parallel Execution

```javascript
// ✅ Good - Parallel execution for independent operations
async function loadGameAssets() {
  const [jokers, cards, sounds] = await Promise.all([
    loadJokerData(),
    loadCardData(),
    loadSoundAssets()
  ]);
  
  return { jokers, cards, sounds };
}

// ✅ Good - Parallel with error handling
async function fetchMultipleResources(urls) {
  try {
    const results = await Promise.allSettled(
      urls.map(url => fetch(url))
    );
    
    return results.map((result, index) => ({
      url: urls[index],
      success: result.status === 'fulfilled',
      data: result.value || null,
      error: result.reason || null
    }));
  } catch (error) {
    console.error('Batch fetch failed:', error);
    throw error;
  }
}
```

### Retry Patterns

```javascript
// ✅ Good - Exponential backoff retry
async function retryWithBackoff(
  fn, 
  maxRetries = 3, 
  baseDelay = 1000
) {
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      if (attempt === maxRetries - 1) {
        throw error;
      }
      
      const delay = baseDelay * Math.pow(2, attempt);
      console.log(`Retry attempt ${attempt + 1} after ${delay}ms`);
      await new Promise(resolve => setTimeout(resolve, delay));
    }
  }
}

// Usage
const gameData = await retryWithBackoff(
  () => fetchGameData(gameId),
  3,
  1000
);
```

## WebSocket Programming

### WebSocket Client Pattern

```javascript
// ✅ Good - Robust WebSocket client implementation
class GameWebSocketClient {
  constructor(url, options = {}) {
    this.url = url;
    this.options = {
      reconnectInterval: 5000,
      maxReconnectAttempts: 5,
      heartbeatInterval: 30000,
      ...options
    };
    
    this.reconnectAttempts = 0;
    this.messageQueue = [];
    this.handlers = new Map();
  }

  connect() {
    return new Promise((resolve, reject) => {
      try {
        // Use wss:// for production
        this.ws = new WebSocket(this.url);
        
        this.ws.onopen = (event) => {
          console.log('WebSocket connected');
          this.reconnectAttempts = 0;
          this.flushMessageQueue();
          this.startHeartbeat();
          resolve(this);
        };
        
        this.ws.onmessage = (event) => {
          this.handleMessage(event.data);
        };
        
        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          reject(error);
        };
        
        this.ws.onclose = (event) => {
          console.log('WebSocket closed:', event.code, event.reason);
          this.stopHeartbeat();
          this.attemptReconnect();
        };
      } catch (error) {
        reject(error);
      }
    });
  }

  send(type, payload) {
    const message = JSON.stringify({ type, payload, timestamp: Date.now() });
    
    if (this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(message);
    } else {
      // Queue messages when disconnected
      this.messageQueue.push(message);
    }
  }

  on(eventType, handler) {
    if (!this.handlers.has(eventType)) {
      this.handlers.set(eventType, new Set());
    }
    this.handlers.get(eventType).add(handler);
  }

  handleMessage(data) {
    try {
      const message = JSON.parse(data);
      const handlers = this.handlers.get(message.type);
      
      if (handlers) {
        handlers.forEach(handler => {
          try {
            handler(message.payload);
          } catch (error) {
            console.error(`Handler error for ${message.type}:`, error);
          }
        });
      }
    } catch (error) {
      console.error('Failed to parse message:', error);
    }
  }

  startHeartbeat() {
    this.heartbeatTimer = setInterval(() => {
      if (this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping' }));
      }
    }, this.options.heartbeatInterval);
  }

  stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  attemptReconnect() {
    if (this.reconnectAttempts >= this.options.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      return;
    }

    this.reconnectAttempts++;
    console.log(`Reconnecting... (attempt ${this.reconnectAttempts})`);
    
    setTimeout(() => {
      this.connect().catch(error => {
        console.error('Reconnection failed:', error);
      });
    }, this.options.reconnectInterval);
  }

  flushMessageQueue() {
    while (this.messageQueue.length > 0) {
      const message = this.messageQueue.shift();
      this.ws.send(message);
    }
  }

  close() {
    this.stopHeartbeat();
    if (this.ws) {
      this.ws.close(1000, 'Client closing connection');
    }
  }
}
```

### Message Protocol

```javascript
// ✅ Good - Structured message format
const MESSAGE_TYPES = {
  // Client -> Server
  JOIN_GAME: 'client:join_game',
  LEAVE_GAME: 'client:leave_game',
  PLAY_HAND: 'client:play_hand',
  
  // Server -> Client
  GAME_STATE: 'server:game_state',
  PLAYER_JOINED: 'server:player_joined',
  ERROR: 'server:error',
  
  // Bidirectional
  PING: 'ping',
  PONG: 'pong'
};

// Message factory
function createMessage(type, payload, metadata = {}) {
  return {
    id: generateMessageId(),
    type,
    payload,
    timestamp: Date.now(),
    version: '1.0',
    ...metadata
  };
}
```

## Event-Driven Architecture

### Event Bus Implementation

```javascript
// ✅ Good - Centralized event bus for decoupled communication
class EventBus {
  constructor() {
    this.events = new Map();
    this.wildcardHandlers = new Set();
  }

  on(eventPattern, handler, options = {}) {
    const { once = false, priority = 0 } = options;
    
    if (eventPattern === '*') {
      this.wildcardHandlers.add({ handler, priority });
      return this;
    }

    if (!this.events.has(eventPattern)) {
      this.events.set(eventPattern, []);
    }

    this.events.get(eventPattern).push({
      handler,
      once,
      priority
    });

    // Sort by priority
    this.events.get(eventPattern).sort((a, b) => b.priority - a.priority);

    return this;
  }

  once(eventPattern, handler) {
    return this.on(eventPattern, handler, { once: true });
  }

  emit(eventType, data) {
    const event = {
      type: eventType,
      data,
      timestamp: Date.now()
    };

    // Emit to specific handlers
    const handlers = this.events.get(eventType) || [];
    const handlersToKeep = [];

    for (const { handler, once } of handlers) {
      try {
        handler(event);
        if (!once) {
          handlersToKeep.push({ handler, once });
        }
      } catch (error) {
        console.error(`Error in handler for ${eventType}:`, error);
      }
    }

    this.events.set(eventType, handlersToKeep);

    // Emit to wildcard handlers
    this.wildcardHandlers.forEach(({ handler }) => {
      try {
        handler(event);
      } catch (error) {
        console.error('Error in wildcard handler:', error);
      }
    });

    return this;
  }

  off(eventPattern, handler) {
    if (eventPattern === '*') {
      this.wildcardHandlers.forEach(item => {
        if (item.handler === handler) {
          this.wildcardHandlers.delete(item);
        }
      });
      return this;
    }

    const handlers = this.events.get(eventPattern);
    if (handlers) {
      this.events.set(
        eventPattern,
        handlers.filter(h => h.handler !== handler)
      );
    }

    return this;
  }

  clear(eventPattern) {
    if (eventPattern) {
      this.events.delete(eventPattern);
    } else {
      this.events.clear();
      this.wildcardHandlers.clear();
    }
    return this;
  }
}

// Usage
const eventBus = new EventBus();

// High priority handler
eventBus.on('game:state:changed', handleCriticalStateChange, { priority: 10 });

// Normal priority handler
eventBus.on('game:state:changed', updateUI);

// Wildcard handler for logging
eventBus.on('*', (event) => {
  console.log(`Event: ${event.type}`, event.data);
});
```

### Event Aggregation Pattern

```javascript
// ✅ Good - Aggregate rapid events for performance
class EventAggregator {
  constructor(options = {}) {
    this.batchWindow = options.batchWindow || 100; // ms
    this.maxBatchSize = options.maxBatchSize || 50;
    this.eventQueue = [];
    this.timer = null;
  }

  push(event) {
    this.eventQueue.push(event);

    if (this.eventQueue.length >= this.maxBatchSize) {
      this.flush();
    } else if (!this.timer) {
      this.timer = setTimeout(() => this.flush(), this.batchWindow);
    }
  }

  flush() {
    if (this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }

    if (this.eventQueue.length === 0) {
      return;
    }

    const events = [...this.eventQueue];
    this.eventQueue = [];

    this.processBatch(events);
  }

  processBatch(events) {
    // Group events by type for efficient processing
    const grouped = events.reduce((acc, event) => {
      if (!acc[event.type]) {
        acc[event.type] = [];
      }
      acc[event.type].push(event);
      return acc;
    }, {});

    // Process each group
    Object.entries(grouped).forEach(([type, groupedEvents]) => {
      this.handleEventGroup(type, groupedEvents);
    });
  }

  handleEventGroup(type, events) {
    // Override in subclass
    console.log(`Processing ${events.length} ${type} events`);
  }
}

// Usage for game state updates
class GameStateAggregator extends EventAggregator {
  handleEventGroup(type, events) {
    if (type === 'card:played') {
      // Aggregate multiple card plays into single update
      const totalCards = events.length;
      const totalScore = events.reduce((sum, e) => sum + e.data.score, 0);
      
      eventBus.emit('game:score:update', {
        cardsPlayed: totalCards,
        scoreGained: totalScore
      });
    }
  }
}
```

## Error Handling

### Custom Error Classes

```javascript
// ✅ Good - Domain-specific error classes
class GameError extends Error {
  constructor(message, code, details = {}) {
    super(message);
    this.name = this.constructor.name;
    this.code = code;
    this.details = details;
    this.timestamp = new Date().toISOString();
    
    // Maintain proper stack trace
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, this.constructor);
    }
  }

  toJSON() {
    return {
      name: this.name,
      message: this.message,
      code: this.code,
      details: this.details,
      timestamp: this.timestamp,
      stack: this.stack
    };
  }
}

class ValidationError extends GameError {
  constructor(message, validationErrors) {
    super(message, 'VALIDATION_ERROR', { validationErrors });
  }
}

class ConnectionError extends GameError {
  constructor(message, cause) {
    super(message, 'CONNECTION_ERROR', { cause });
  }
}

// Usage
function validateGameMove(move) {
  const errors = [];
  
  if (!move.playerId) {
    errors.push({ field: 'playerId', message: 'Player ID is required' });
  }
  
  if (!move.cards || move.cards.length === 0) {
    errors.push({ field: 'cards', message: 'At least one card must be played' });
  }
  
  if (errors.length > 0) {
    throw new ValidationError('Invalid game move', errors);
  }
}
```

### Error Handling Patterns

```javascript
// ✅ Good - Centralized error handler
class ErrorHandler {
  constructor(options = {}) {
    this.logger = options.logger || console;
    this.handlers = new Map();
    
    // Register default handlers
    this.register(ValidationError, this.handleValidationError.bind(this));
    this.register(ConnectionError, this.handleConnectionError.bind(this));
  }

  register(errorType, handler) {
    this.handlers.set(errorType, handler);
  }

  handle(error) {
    // Check for specific handler
    for (const [ErrorType, handler] of this.handlers) {
      if (error instanceof ErrorType) {
        return handler(error);
      }
    }
    
    // Default handling
    this.handleGenericError(error);
  }

  handleValidationError(error) {
    this.logger.warn('Validation error:', {
      message: error.message,
      errors: error.details.validationErrors
    });
    
    return {
      success: false,
      error: {
        type: 'validation',
        message: error.message,
        fields: error.details.validationErrors
      }
    };
  }

  handleConnectionError(error) {
    this.logger.error('Connection error:', {
      message: error.message,
      cause: error.details.cause
    });
    
    return {
      success: false,
      error: {
        type: 'connection',
        message: 'Unable to connect to game server',
        retryable: true
      }
    };
  }

  handleGenericError(error) {
    this.logger.error('Unhandled error:', error);
    
    return {
      success: false,
      error: {
        type: 'unknown',
        message: 'An unexpected error occurred'
      }
    };
  }
}

// Global error handler for unhandled rejections
process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
  // Application specific logging mechanism here
});
```

## Testing Conventions

### Test Structure

```javascript
// ✅ Good - Descriptive test structure
describe('GameWebSocketClient', () => {
  let client;
  let mockWebSocket;
  
  beforeEach(() => {
    mockWebSocket = new MockWebSocket();
    global.WebSocket = jest.fn(() => mockWebSocket);
    client = new GameWebSocketClient('ws://localhost:3000');
  });
  
  afterEach(() => {
    client.close();
    jest.restoreAllMocks();
  });
  
  describe('connection handling', () => {
    it('should establish connection successfully', async () => {
      const connectionPromise = client.connect();
      mockWebSocket.triggerOpen();
      
      await expect(connectionPromise).resolves.toBe(client);
      expect(client.ws.readyState).toBe(WebSocket.OPEN);
    });
    
    it('should handle connection errors', async () => {
      const connectionPromise = client.connect();
      const error = new Error('Connection refused');
      mockWebSocket.triggerError(error);
      
      await expect(connectionPromise).rejects.toThrow('Connection refused');
    });
    
    it('should queue messages when disconnected', () => {
      client.send('test:message', { data: 'test' });
      
      expect(client.messageQueue).toHaveLength(1);
      expect(mockWebSocket.send).not.toHaveBeenCalled();
    });
  });
  
  describe('reconnection logic', () => {
    it('should attempt reconnection on disconnect', async () => {
      jest.useFakeTimers();
      
      await client.connect();
      mockWebSocket.triggerClose({ code: 1006 });
      
      expect(client.reconnectAttempts).toBe(1);
      
      jest.advanceTimersByTime(5000);
      expect(global.WebSocket).toHaveBeenCalledTimes(2);
      
      jest.useRealTimers();
    });
  });
});
```

### Async Testing

```javascript
// ✅ Good - Testing async operations
describe('EventAggregator', () => {
  let aggregator;
  let processSpy;
  
  beforeEach(() => {
    aggregator = new EventAggregator({ 
      batchWindow: 50,
      maxBatchSize: 3 
    });
    processSpy = jest.spyOn(aggregator, 'processBatch');
  });
  
  it('should batch events within time window', async () => {
    aggregator.push({ type: 'test', data: 1 });
    aggregator.push({ type: 'test', data: 2 });
    
    expect(processSpy).not.toHaveBeenCalled();
    
    // Wait for batch window
    await new Promise(resolve => setTimeout(resolve, 60));
    
    expect(processSpy).toHaveBeenCalledWith([
      { type: 'test', data: 1 },
      { type: 'test', data: 2 }
    ]);
  });
  
  it('should flush immediately when max batch size reached', () => {
    aggregator.push({ type: 'test', data: 1 });
    aggregator.push({ type: 'test', data: 2 });
    aggregator.push({ type: 'test', data: 3 });
    
    expect(processSpy).toHaveBeenCalledTimes(1);
  });
});
```

### Mock Patterns

```javascript
// ✅ Good - Creating reusable mocks
class MockWebSocket {
  constructor() {
    this.readyState = WebSocket.CONNECTING;
    this.send = jest.fn();
    this.close = jest.fn();
    this.addEventListener = jest.fn();
    this.removeEventListener = jest.fn();
  }
  
  triggerOpen() {
    this.readyState = WebSocket.OPEN;
    this.onopen?.({ type: 'open' });
  }
  
  triggerMessage(data) {
    this.onmessage?.({ 
      type: 'message', 
      data: typeof data === 'string' ? data : JSON.stringify(data) 
    });
  }
  
  triggerError(error) {
    this.onerror?.(error);
  }
  
  triggerClose(event = {}) {
    this.readyState = WebSocket.CLOSED;
    this.onclose?.({ 
      type: 'close',
      code: event.code || 1000,
      reason: event.reason || ''
    });
  }
}

// Mock event bus for testing
function createMockEventBus() {
  const events = [];
  
  return {
    emit: jest.fn((type, data) => {
      events.push({ type, data, timestamp: Date.now() });
    }),
    on: jest.fn(),
    off: jest.fn(),
    getEvents: () => [...events],
    clear: () => { events.length = 0; }
  };
}
```

## Code Quality

### ESLint Configuration

```javascript
// .eslintrc.js
module.exports = {
  env: {
    browser: true,
    es2021: true,
    node: true,
    jest: true
  },
  extends: [
    'eslint:recommended',
    'plugin:promise/recommended'
  ],
  parserOptions: {
    ecmaVersion: 2022,
    sourceType: 'module'
  },
  rules: {
    // Variables
    'no-var': 'error',
    'prefer-const': 'error',
    
    // Functions
    'arrow-body-style': ['error', 'as-needed'],
    'prefer-arrow-callback': 'error',
    
    // Async
    'no-async-promise-executor': 'error',
    'require-await': 'error',
    
    // Best practices
    'no-console': ['warn', { allow: ['warn', 'error'] }],
    'eqeqeq': ['error', 'always', { null: 'ignore' }],
    'no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
    
    // Style
    'quotes': ['error', 'single', { avoidEscape: true }],
    'semi': ['error', 'always'],
    'comma-dangle': ['error', 'never'],
    'indent': ['error', 2, { SwitchCase: 1 }]
  }
};
```

### Documentation with JSDoc

```javascript
/**
 * Manages WebSocket connections for real-time game communication
 * @class
 * @example
 * const client = new GameWebSocketClient('wss://game.example.com');
 * await client.connect();
 * client.on('game:update', (data) => console.log(data));
 */
class GameWebSocketClient {
  /**
   * Creates a new WebSocket client
   * @param {string} url - WebSocket server URL
   * @param {Object} [options={}] - Configuration options
   * @param {number} [options.reconnectInterval=5000] - Time between reconnection attempts
   * @param {number} [options.maxReconnectAttempts=5] - Maximum reconnection attempts
   * @param {number} [options.heartbeatInterval=30000] - Heartbeat interval in ms
   */
  constructor(url, options = {}) {
    // Implementation
  }
  
  /**
   * Establishes WebSocket connection
   * @returns {Promise<GameWebSocketClient>} Resolves when connected
   * @throws {ConnectionError} When connection fails
   */
  async connect() {
    // Implementation
  }
  
  /**
   * Sends a message to the server
   * @param {string} type - Message type
   * @param {*} payload - Message payload
   * @returns {void}
   */
  send(type, payload) {
    // Implementation
  }
}
```

## Summary

This style guide emphasizes:

1. **Modern JavaScript**: Use ES6+ features, async/await, and ES modules
2. **Robust Error Handling**: Custom error classes and centralized handling
3. **Event-Driven Patterns**: Decoupled components with event bus architecture
4. **Real-Time Communication**: Resilient WebSocket implementations with reconnection
5. **Performance**: Event aggregation and efficient async patterns
6. **Testing**: Comprehensive test coverage with proper mocking
7. **Code Quality**: Consistent formatting and thorough documentation

Follow these patterns to build maintainable, scalable real-time applications suitable for game mods and similar event-driven systems.