# TypeScript Style Guide

This style guide provides comprehensive conventions for TypeScript development in the JimBot project, building upon the JavaScript style guide with TypeScript-specific patterns for type safety, interfaces, and advanced features.

## Table of Contents

1. [TypeScript Configuration](#typescript-configuration)
2. [Type System](#type-system)
3. [Interfaces and Types](#interfaces-and-types)
4. [Generics](#generics)
5. [Enums and Constants](#enums-and-constants)
6. [Classes and Decorators](#classes-and-decorators)
7. [Module System](#module-system)
8. [Async Patterns with Types](#async-patterns-with-types)
9. [WebSocket and Event Types](#websocket-and-event-types)
10. [Error Handling with Types](#error-handling-with-types)
11. [Testing TypeScript](#testing-typescript)

## TypeScript Configuration

### Strict Mode Configuration (tsconfig.json)

```json
{
  "compilerOptions": {
    // Type Safety
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "strictFunctionTypes": true,
    "strictBindCallApply": true,
    "strictPropertyInitialization": true,
    "noImplicitThis": true,
    "alwaysStrict": true,
    
    // Additional Strictness
    "noUncheckedIndexedAccess": true,
    "exactOptionalPropertyTypes": true,
    "noImplicitOverride": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "allowUnreachableCode": false,
    "allowUnusedLabels": false,
    "noPropertyAccessFromIndexSignature": true,
    
    // Module System
    "target": "ES2022",
    "module": "ES2022",
    "moduleResolution": "node",
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "verbatimModuleSyntax": true,
    
    // Output
    "outDir": "./dist",
    "rootDir": "./src",
    "declaration": true,
    "declarationMap": true,
    "sourceMap": true,
    "removeComments": false,
    
    // Other
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "lib": ["ES2022", "DOM"]
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist", "**/*.test.ts"]
}
```

## Type System

### Basic Types and Type Annotations

```typescript
// ✅ Good - Explicit types for clarity
const MAX_RETRIES: number = 3;
const GAME_ID: string = 'game_12345';
const IS_ACTIVE: boolean = true;
const JOKER_IDS: readonly string[] = ['J1', 'J2', 'J3'];

// ✅ Good - Type inference when obvious
const playerCount = 4; // number
const playerName = 'JimBot'; // string

// ✅ Good - Union types
type GameState = 'idle' | 'playing' | 'paused' | 'ended';
let currentState: GameState = 'idle';

// ✅ Good - Tuple types
type Coordinate = [x: number, y: number];
const position: Coordinate = [10, 20];

// ✅ Good - Object types with index signatures
interface ScoreMap {
  [playerId: string]: number;
}

// ❌ Bad - Using any
let data: any; // Avoid any unless absolutely necessary
```

### Type Guards and Narrowing

```typescript
// ✅ Good - Type predicate functions
interface Card {
  suit: string;
  rank: string;
}

interface Joker {
  name: string;
  effect: string;
}

type GameItem = Card | Joker;

function isCard(item: GameItem): item is Card {
  return 'suit' in item && 'rank' in item;
}

function isJoker(item: GameItem): item is Joker {
  return 'name' in item && 'effect' in item;
}

// Usage with narrowing
function processGameItem(item: GameItem): void {
  if (isCard(item)) {
    console.log(`Card: ${item.suit} ${item.rank}`);
  } else if (isJoker(item)) {
    console.log(`Joker: ${item.name} - ${item.effect}`);
  }
}

// ✅ Good - Discriminated unions
interface SuccessResponse {
  status: 'success';
  data: unknown;
}

interface ErrorResponse {
  status: 'error';
  error: {
    code: string;
    message: string;
  };
}

type ApiResponse = SuccessResponse | ErrorResponse;

function handleResponse(response: ApiResponse): void {
  switch (response.status) {
    case 'success':
      processData(response.data);
      break;
    case 'error':
      handleError(response.error);
      break;
  }
}
```

### Utility Types

```typescript
// ✅ Good - Using built-in utility types
interface GameConfig {
  maxPlayers: number;
  difficulty: string;
  soundEnabled: boolean;
  graphicsQuality: 'low' | 'medium' | 'high';
}

// Partial for optional updates
type GameConfigUpdate = Partial<GameConfig>;

// Readonly for immutable data
type ImmutableGameConfig = Readonly<GameConfig>;

// Pick for subsets
type AudioConfig = Pick<GameConfig, 'soundEnabled'>;

// Omit for exclusions
type GameConfigWithoutAudio = Omit<GameConfig, 'soundEnabled'>;

// Record for dictionaries
type PlayerScores = Record<string, number>;

// ✅ Good - Custom utility types
type Nullable<T> = T | null;
type Optional<T> = T | undefined;
type Nullish<T> = T | null | undefined;

// Deep readonly
type DeepReadonly<T> = {
  readonly [P in keyof T]: T[P] extends object ? DeepReadonly<T[P]> : T[P];
};
```

## Interfaces and Types

### Interface vs Type Alias

```typescript
// ✅ Good - Use interfaces for object shapes that might be extended
interface Player {
  id: string;
  name: string;
  score: number;
}

interface PremiumPlayer extends Player {
  subscription: {
    tier: 'gold' | 'platinum';
    expiresAt: Date;
  };
}

// ✅ Good - Use type aliases for unions, tuples, and complex types
type PlayerId = string;
type Score = number;
type GameResult = 'win' | 'loss' | 'draw';
type PlayerTuple = [id: PlayerId, score: Score];

// ✅ Good - Combining interfaces and types
interface BaseEvent {
  id: string;
  timestamp: number;
}

type GameEvent = BaseEvent & {
  type: 'game_start' | 'game_end' | 'score_update';
  gameId: string;
};

type PlayerEvent = BaseEvent & {
  type: 'player_join' | 'player_leave' | 'player_action';
  playerId: string;
};

type Event = GameEvent | PlayerEvent;
```

### Interface Best Practices

```typescript
// ✅ Good - Prefixing interfaces (optional but consistent)
interface IGameEngine {
  start(): void;
  stop(): void;
  getState(): GameState;
}

// ✅ Good - Readonly properties
interface GameStats {
  readonly gameId: string;
  readonly startTime: Date;
  endTime?: Date;
  readonly players: ReadonlyArray<Player>;
}

// ✅ Good - Method signatures
interface EventHandler<T = unknown> {
  (event: T): void | Promise<void>;
}

interface EventEmitter<TEvents extends Record<string, unknown>> {
  on<K extends keyof TEvents>(event: K, handler: EventHandler<TEvents[K]>): void;
  off<K extends keyof TEvents>(event: K, handler: EventHandler<TEvents[K]>): void;
  emit<K extends keyof TEvents>(event: K, data: TEvents[K]): void;
}

// ✅ Good - Optional properties with exact types
interface ServerConfig {
  host: string;
  port: number;
  ssl?: {
    cert: string;
    key: string;
  };
  // exactOptionalPropertyTypes ensures ssl is { cert, key } | undefined, not { cert, key } | undefined | { cert?, key? }
}
```

## Generics

### Generic Functions

```typescript
// ✅ Good - Generic with constraints
function getProperty<T, K extends keyof T>(obj: T, key: K): T[K] {
  return obj[key];
}

// ✅ Good - Multiple generic parameters
function merge<T extends object, U extends object>(
  first: T,
  second: U
): T & U {
  return { ...first, ...second };
}

// ✅ Good - Generic with default
function createArray<T = string>(length: number, value: T): T[] {
  return Array(length).fill(value);
}

// ✅ Good - Conditional types in generics
type AsyncReturnType<T extends (...args: any[]) => Promise<any>> = 
  T extends (...args: any[]) => Promise<infer R> ? R : never;

// Usage
async function fetchUser(): Promise<User> {
  // Implementation
}

type UserType = AsyncReturnType<typeof fetchUser>; // User
```

### Generic Classes

```typescript
// ✅ Good - Generic event queue
class EventQueue<T> {
  private items: T[] = [];
  
  enqueue(item: T): void {
    this.items.push(item);
  }
  
  dequeue(): T | undefined {
    return this.items.shift();
  }
  
  peek(): T | undefined {
    return this.items[0];
  }
  
  get size(): number {
    return this.items.length;
  }
}

// ✅ Good - Generic state manager
class StateManager<TState extends Record<string, unknown>> {
  private state: TState;
  private listeners = new Set<(state: TState) => void>();
  
  constructor(initialState: TState) {
    this.state = { ...initialState };
  }
  
  getState(): Readonly<TState> {
    return Object.freeze({ ...this.state });
  }
  
  setState<K extends keyof TState>(
    key: K,
    value: TState[K]
  ): void {
    this.state[key] = value;
    this.notifyListeners();
  }
  
  subscribe(listener: (state: TState) => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }
  
  private notifyListeners(): void {
    this.listeners.forEach(listener => listener(this.getState()));
  }
}
```

## Enums and Constants

### String Enums (Preferred)

```typescript
// ✅ Good - String enums for better debugging and serialization
enum GameEvent {
  Start = 'GAME_START',
  End = 'GAME_END',
  Pause = 'GAME_PAUSE',
  Resume = 'GAME_RESUME'
}

enum ErrorCode {
  InvalidMove = 'INVALID_MOVE',
  Unauthorized = 'UNAUTHORIZED',
  GameFull = 'GAME_FULL',
  ConnectionLost = 'CONNECTION_LOST'
}

// ✅ Good - Const enums for performance (when not needed at runtime)
const enum Direction {
  Up = 'UP',
  Down = 'DOWN',
  Left = 'LEFT',
  Right = 'RIGHT'
}
```

### Const Assertions

```typescript
// ✅ Good - Object as const for type safety
const GAME_CONFIG = {
  MAX_PLAYERS: 4,
  MIN_PLAYERS: 2,
  ROUND_TIME: 60,
  DIFFICULTIES: ['easy', 'medium', 'hard']
} as const;

type Difficulty = typeof GAME_CONFIG.DIFFICULTIES[number]; // 'easy' | 'medium' | 'hard'

// ✅ Good - Const assertion for literal types
const createMessage = <T extends string>(type: T) => {
  return {
    type,
    timestamp: Date.now()
  } as const;
};

const msg = createMessage('USER_LOGIN'); // type is { readonly type: "USER_LOGIN"; readonly timestamp: number }
```

## Classes and Decorators

### Class Design

```typescript
// ✅ Good - Class with proper visibility modifiers
class GameSession {
  private readonly id: string;
  private players: Map<string, Player>;
  private _state: GameState;
  
  public readonly maxPlayers: number;
  public readonly createdAt: Date;
  
  constructor(config: GameSessionConfig) {
    this.id = generateId();
    this.players = new Map();
    this._state = 'waiting';
    this.maxPlayers = config.maxPlayers;
    this.createdAt = new Date();
  }
  
  // Getter with return type
  public get state(): GameState {
    return this._state;
  }
  
  // Method with explicit return type
  public addPlayer(player: Player): boolean {
    if (this.players.size >= this.maxPlayers) {
      return false;
    }
    
    this.players.set(player.id, player);
    return true;
  }
  
  // Protected method for subclasses
  protected setState(newState: GameState): void {
    this._state = newState;
    this.onStateChange(newState);
  }
  
  // Abstract-like method (override in subclasses)
  protected onStateChange(newState: GameState): void {
    // Default implementation
    console.log(`State changed to: ${newState}`);
  }
}

// ✅ Good - Abstract classes
abstract class BaseGameMode {
  abstract readonly name: string;
  abstract readonly minPlayers: number;
  
  abstract calculateScore(moves: Move[]): number;
  
  // Concrete method
  public validateMove(move: Move): boolean {
    return this.isValidMove(move);
  }
  
  protected abstract isValidMove(move: Move): boolean;
}
```

### Decorators (when using experimental features)

```typescript
// ✅ Good - Method decorators for common patterns
function debounce(delay: number) {
  return function (
    target: any,
    propertyKey: string,
    descriptor: PropertyDescriptor
  ): PropertyDescriptor {
    let timeout: NodeJS.Timeout;
    
    const originalMethod = descriptor.value;
    
    descriptor.value = function (...args: any[]) {
      clearTimeout(timeout);
      timeout = setTimeout(() => {
        originalMethod.apply(this, args);
      }, delay);
    };
    
    return descriptor;
  };
}

function memoize() {
  return function (
    target: any,
    propertyKey: string,
    descriptor: PropertyDescriptor
  ): PropertyDescriptor {
    const cache = new Map();
    const originalMethod = descriptor.value;
    
    descriptor.value = function (...args: any[]) {
      const key = JSON.stringify(args);
      
      if (cache.has(key)) {
        return cache.get(key);
      }
      
      const result = originalMethod.apply(this, args);
      cache.set(key, result);
      return result;
    };
    
    return descriptor;
  };
}

// Usage
class GameAnalytics {
  @debounce(1000)
  public trackEvent(event: AnalyticsEvent): void {
    // Will be debounced
  }
  
  @memoize()
  public calculateComplexScore(gameData: GameData): number {
    // Result will be cached
    return complexCalculation(gameData);
  }
}
```

## Module System

### ES Modules with TypeScript

```typescript
// ✅ Good - Named exports with types
// types/game.ts
export interface Game {
  id: string;
  players: Player[];
  state: GameState;
}

export type GameState = 'waiting' | 'playing' | 'finished';

export interface Player {
  id: string;
  name: string;
  score: number;
}

// ✅ Good - Barrel exports
// types/index.ts
export * from './game';
export * from './events';
export * from './errors';

// ✅ Good - Default export for main class
// services/GameService.ts
export default class GameService {
  // Implementation
}

export { GameService }; // Also export as named for better tree-shaking

// ✅ Good - Type-only imports
import type { Game, Player } from './types';
import { type GameState } from './types'; // Alternative syntax
```

### Module Augmentation

```typescript
// ✅ Good - Extending existing modules
declare module 'express' {
  interface Request {
    gameSession?: GameSession;
    player?: Player;
  }
}

// ✅ Good - Global augmentation
declare global {
  interface Window {
    gameClient: GameClient;
  }
  
  namespace NodeJS {
    interface ProcessEnv {
      GAME_SERVER_URL: string;
      GAME_API_KEY: string;
      NODE_ENV: 'development' | 'production' | 'test';
    }
  }
}
```

## Async Patterns with Types

### Typed Promises

```typescript
// ✅ Good - Explicit Promise types
interface ApiClient {
  fetchGame(id: string): Promise<Game>;
  updateScore(playerId: string, score: number): Promise<void>;
  listGames(filter?: GameFilter): Promise<Game[]>;
}

// ✅ Good - Generic async function
async function retry<T>(
  fn: () => Promise<T>,
  options: {
    maxAttempts?: number;
    delay?: number;
    onError?: (error: Error, attempt: number) => void;
  } = {}
): Promise<T> {
  const { maxAttempts = 3, delay = 1000, onError } = options;
  
  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    try {
      return await fn();
    } catch (error) {
      if (attempt === maxAttempts) {
        throw error;
      }
      
      onError?.(error as Error, attempt);
      await new Promise(resolve => setTimeout(resolve, delay * attempt));
    }
  }
  
  throw new Error('Unexpected retry failure');
}

// ✅ Good - Result type pattern
type Result<T, E = Error> = 
  | { success: true; data: T }
  | { success: false; error: E };

async function safeAsync<T>(
  fn: () => Promise<T>
): Promise<Result<T>> {
  try {
    const data = await fn();
    return { success: true, data };
  } catch (error) {
    return { success: false, error: error as Error };
  }
}
```

### Async Generators

```typescript
// ✅ Good - Typed async generators
async function* gameEventStream(
  gameId: string
): AsyncGenerator<GameEvent, void, unknown> {
  const eventSource = new EventSource(`/games/${gameId}/events`);
  
  try {
    while (true) {
      const event = await waitForEvent(eventSource);
      yield parseGameEvent(event);
    }
  } finally {
    eventSource.close();
  }
}

// Usage with type safety
async function processGameEvents(gameId: string): Promise<void> {
  for await (const event of gameEventStream(gameId)) {
    switch (event.type) {
      case 'player_joined':
        handlePlayerJoined(event.playerId);
        break;
      case 'score_update':
        updateScore(event.playerId, event.score);
        break;
    }
  }
}
```

## WebSocket and Event Types

### Strongly Typed WebSocket Messages

```typescript
// ✅ Good - Message type system
interface ClientMessages {
  'client:join': {
    playerId: string;
    gameId: string;
  };
  'client:move': {
    playerId: string;
    move: Move;
  };
  'client:chat': {
    playerId: string;
    message: string;
  };
}

interface ServerMessages {
  'server:joined': {
    gameState: GameState;
    players: Player[];
  };
  'server:move': {
    playerId: string;
    move: Move;
    newState: GameState;
  };
  'server:error': {
    code: ErrorCode;
    message: string;
  };
}

type ClientMessageType = keyof ClientMessages;
type ServerMessageType = keyof ServerMessages;

// ✅ Good - Type-safe WebSocket client
class TypedWebSocketClient<
  TSend extends Record<string, unknown>,
  TReceive extends Record<string, unknown>
> {
  private ws: WebSocket;
  private handlers = new Map<keyof TReceive, Set<(data: any) => void>>();
  
  constructor(url: string) {
    this.ws = new WebSocket(url);
    this.setupEventHandlers();
  }
  
  public send<K extends keyof TSend>(type: K, data: TSend[K]): void {
    if (this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, data }));
    }
  }
  
  public on<K extends keyof TReceive>(
    type: K,
    handler: (data: TReceive[K]) => void
  ): void {
    if (!this.handlers.has(type)) {
      this.handlers.set(type, new Set());
    }
    this.handlers.get(type)!.add(handler);
  }
  
  private setupEventHandlers(): void {
    this.ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        const handlers = this.handlers.get(message.type);
        
        handlers?.forEach(handler => handler(message.data));
      } catch (error) {
        console.error('Failed to parse message:', error);
      }
    };
  }
}

// Usage
const client = new TypedWebSocketClient<ClientMessages, ServerMessages>('wss://game.example.com');

client.on('server:joined', (data) => {
  // data is typed as { gameState: GameState; players: Player[] }
  console.log(`Joined game with ${data.players.length} players`);
});

client.send('client:join', {
  playerId: 'player123',
  gameId: 'game456'
});
```

### Event Emitter with Types

```typescript
// ✅ Good - Strongly typed event emitter
type EventMap = Record<string, unknown>;

interface TypedEventEmitter<TEvents extends EventMap> {
  on<K extends keyof TEvents>(
    event: K,
    listener: (data: TEvents[K]) => void
  ): this;
  
  once<K extends keyof TEvents>(
    event: K,
    listener: (data: TEvents[K]) => void
  ): this;
  
  emit<K extends keyof TEvents>(
    event: K,
    data: TEvents[K]
  ): boolean;
  
  off<K extends keyof TEvents>(
    event: K,
    listener: (data: TEvents[K]) => void
  ): this;
  
  removeAllListeners<K extends keyof TEvents>(event?: K): this;
}

// Implementation
class GameEventEmitter<TEvents extends EventMap> 
  implements TypedEventEmitter<TEvents> {
  private events = new Map<keyof TEvents, Set<Function>>();
  
  on<K extends keyof TEvents>(
    event: K,
    listener: (data: TEvents[K]) => void
  ): this {
    if (!this.events.has(event)) {
      this.events.set(event, new Set());
    }
    this.events.get(event)!.add(listener);
    return this;
  }
  
  // ... other methods
}

// Usage with specific events
interface GameEvents {
  'game:start': { gameId: string; timestamp: number };
  'game:end': { gameId: string; winner: string; finalScores: Record<string, number> };
  'player:join': { playerId: string; playerName: string };
  'player:leave': { playerId: string; reason: string };
}

const gameEvents = new GameEventEmitter<GameEvents>();

gameEvents.on('game:start', ({ gameId, timestamp }) => {
  // Fully typed parameters
  console.log(`Game ${gameId} started at ${new Date(timestamp)}`);
});
```

## Error Handling with Types

### Custom Error Classes

```typescript
// ✅ Good - Base error class with generics
abstract class BaseError<TCode extends string = string> extends Error {
  public abstract readonly code: TCode;
  public readonly timestamp: Date;
  public readonly context?: unknown;
  
  constructor(message: string, context?: unknown) {
    super(message);
    this.name = this.constructor.name;
    this.timestamp = new Date();
    this.context = context;
    
    // Maintains proper stack trace for where our error was thrown
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, this.constructor);
    }
  }
  
  public toJSON(): Record<string, unknown> {
    return {
      name: this.name,
      code: this.code,
      message: this.message,
      timestamp: this.timestamp,
      context: this.context,
      stack: this.stack
    };
  }
}

// ✅ Good - Specific error types
class ValidationError extends BaseError<'VALIDATION_ERROR'> {
  public readonly code = 'VALIDATION_ERROR' as const;
  public readonly validationErrors: Array<{
    field: string;
    message: string;
  }>;
  
  constructor(
    message: string,
    validationErrors: Array<{ field: string; message: string }>
  ) {
    super(message, { validationErrors });
    this.validationErrors = validationErrors;
  }
}

class GameError extends BaseError<GameErrorCode> {
  constructor(
    public readonly code: GameErrorCode,
    message: string,
    context?: unknown
  ) {
    super(message, context);
  }
}

type GameErrorCode = 
  | 'GAME_NOT_FOUND'
  | 'GAME_FULL'
  | 'INVALID_MOVE'
  | 'NOT_YOUR_TURN';

// ✅ Good - Error factory pattern
class ErrorFactory {
  static validation(
    field: string,
    message: string
  ): ValidationError {
    return new ValidationError('Validation failed', [{ field, message }]);
  }
  
  static gameNotFound(gameId: string): GameError {
    return new GameError(
      'GAME_NOT_FOUND',
      `Game with ID ${gameId} not found`,
      { gameId }
    );
  }
  
  static invalidMove(move: Move, reason: string): GameError {
    return new GameError(
      'INVALID_MOVE',
      `Invalid move: ${reason}`,
      { move, reason }
    );
  }
}
```

### Error Handling Utilities

```typescript
// ✅ Good - Type-safe error handling
function isErrorOfType<T extends BaseError>(
  error: unknown,
  errorClass: new (...args: any[]) => T
): error is T {
  return error instanceof errorClass;
}

function assertNever(value: never): never {
  throw new Error(`Unexpected value: ${value}`);
}

// ✅ Good - Result type with error handling
class ResultWrapper<T, E extends Error = Error> {
  private constructor(
    private readonly value: T | null,
    private readonly error: E | null
  ) {}
  
  static ok<T>(value: T): ResultWrapper<T, never> {
    return new ResultWrapper(value, null);
  }
  
  static err<E extends Error>(error: E): ResultWrapper<never, E> {
    return new ResultWrapper(null, error);
  }
  
  isOk(): this is ResultWrapper<T, never> {
    return this.error === null;
  }
  
  isErr(): this is ResultWrapper<never, E> {
    return this.error !== null;
  }
  
  unwrap(): T {
    if (this.error) {
      throw this.error;
    }
    return this.value!;
  }
  
  unwrapOr(defaultValue: T): T {
    return this.error ? defaultValue : this.value!;
  }
  
  map<U>(fn: (value: T) => U): ResultWrapper<U, E> {
    if (this.error) {
      return ResultWrapper.err(this.error);
    }
    return ResultWrapper.ok(fn(this.value!));
  }
}

// Usage
async function parseGameConfig(
  data: string
): Promise<ResultWrapper<GameConfig, ValidationError>> {
  try {
    const parsed = JSON.parse(data);
    const validated = validateGameConfig(parsed);
    return ResultWrapper.ok(validated);
  } catch (error) {
    if (error instanceof ValidationError) {
      return ResultWrapper.err(error);
    }
    return ResultWrapper.err(
      new ValidationError('Invalid config format', [])
    );
  }
}
```

## Testing TypeScript

### Type-Safe Test Utilities

```typescript
// ✅ Good - Mock factories with types
function createMockPlayer(overrides?: Partial<Player>): Player {
  return {
    id: 'player_test_123',
    name: 'Test Player',
    score: 0,
    ...overrides
  };
}

function createMockWebSocket(): jest.Mocked<WebSocket> {
  return {
    readyState: WebSocket.CONNECTING,
    send: jest.fn(),
    close: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
    onopen: null,
    onclose: null,
    onerror: null,
    onmessage: null,
    binaryType: 'blob',
    bufferedAmount: 0,
    extensions: '',
    protocol: '',
    url: 'ws://localhost:3000',
    CONNECTING: 0,
    OPEN: 1,
    CLOSING: 2,
    CLOSED: 3
  };
}

// ✅ Good - Type-safe test builders
class GameTestBuilder {
  private game: Partial<Game> = {};
  
  withId(id: string): this {
    this.game.id = id;
    return this;
  }
  
  withPlayers(...players: Player[]): this {
    this.game.players = players;
    return this;
  }
  
  withState(state: GameState): this {
    this.game.state = state;
    return this;
  }
  
  build(): Game {
    return {
      id: this.game.id ?? 'test_game_123',
      players: this.game.players ?? [],
      state: this.game.state ?? 'waiting'
    };
  }
}

// Usage
const game = new GameTestBuilder()
  .withId('game_456')
  .withPlayers(createMockPlayer({ name: 'Alice' }))
  .withState('playing')
  .build();
```

### Testing Async Code

```typescript
// ✅ Good - Type-safe async testing
describe('GameService', () => {
  let service: GameService;
  let mockClient: jest.Mocked<ApiClient>;
  
  beforeEach(() => {
    mockClient = {
      fetchGame: jest.fn(),
      updateScore: jest.fn(),
      listGames: jest.fn()
    };
    
    service = new GameService(mockClient);
  });
  
  describe('getGame', () => {
    it('should return game when found', async () => {
      const expectedGame = new GameTestBuilder().build();
      mockClient.fetchGame.mockResolvedValue(expectedGame);
      
      const result = await service.getGame('game_123');
      
      expect(result).toEqual(expectedGame);
      expect(mockClient.fetchGame).toHaveBeenCalledWith('game_123');
    });
    
    it('should handle errors correctly', async () => {
      const error = new GameError('GAME_NOT_FOUND', 'Game not found');
      mockClient.fetchGame.mockRejectedValue(error);
      
      await expect(service.getGame('invalid_id')).rejects.toThrow(error);
    });
  });
});

// ✅ Good - Testing event emitters
describe('GameEventEmitter', () => {
  let emitter: GameEventEmitter<GameEvents>;
  
  beforeEach(() => {
    emitter = new GameEventEmitter();
  });
  
  it('should emit typed events', (done) => {
    emitter.on('game:start', (data) => {
      expect(data.gameId).toBe('test_123');
      expect(data.timestamp).toBeGreaterThan(0);
      done();
    });
    
    emitter.emit('game:start', {
      gameId: 'test_123',
      timestamp: Date.now()
    });
  });
});
```

## Linting and Formatting

### ESLint Configuration for TypeScript

```javascript
// .eslintrc.js
module.exports = {
  parser: '@typescript-eslint/parser',
  parserOptions: {
    ecmaVersion: 2022,
    sourceType: 'module',
    project: './tsconfig.json'
  },
  plugins: ['@typescript-eslint'],
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:@typescript-eslint/recommended-requiring-type-checking'
  ],
  rules: {
    // TypeScript specific rules
    '@typescript-eslint/explicit-function-return-type': ['error', {
      allowExpressions: true,
      allowTypedFunctionExpressions: true
    }],
    '@typescript-eslint/no-explicit-any': 'error',
    '@typescript-eslint/no-unused-vars': ['error', {
      argsIgnorePattern: '^_',
      varsIgnorePattern: '^_'
    }],
    '@typescript-eslint/consistent-type-imports': ['error', {
      prefer: 'type-imports'
    }],
    '@typescript-eslint/no-floating-promises': 'error',
    '@typescript-eslint/no-misused-promises': 'error',
    '@typescript-eslint/await-thenable': 'error',
    '@typescript-eslint/no-unnecessary-type-assertion': 'error',
    '@typescript-eslint/prefer-nullish-coalescing': 'error',
    '@typescript-eslint/prefer-optional-chain': 'error',
    
    // General rules
    'no-console': ['warn', { allow: ['warn', 'error'] }],
    'prefer-const': 'error'
  }
};
```

### Prettier Configuration

```json
// .prettierrc
{
  "semi": true,
  "trailingComma": "es5",
  "singleQuote": true,
  "printWidth": 80,
  "tabWidth": 2,
  "useTabs": false,
  "arrowParens": "always",
  "endOfLine": "lf"
}
```

## Summary

This TypeScript style guide emphasizes:

1. **Type Safety**: Leverage TypeScript's type system fully with strict mode
2. **Explicit Types**: Use explicit types for public APIs and complex logic
3. **Type Guards**: Implement proper type narrowing for runtime safety
4. **Generics**: Use generic types for reusable, type-safe components
5. **Error Handling**: Strongly typed errors with proper error hierarchies
6. **Async Patterns**: Type-safe Promise and async/await patterns
7. **Event Systems**: Fully typed event emitters and WebSocket communication
8. **Testing**: Comprehensive type-safe testing utilities and patterns

Following these patterns ensures type safety, better IDE support, easier refactoring, and more maintainable code in real-time, event-driven applications.