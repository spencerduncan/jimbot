# High-Performance C++ Style Guide for Memgraph MAGE Modules

This guide synthesizes best practices from Google C++ Style Guide, C++ Core
Guidelines, LLVM Coding Standards, and modern C++ (C++17/20) for developing
high-performance graph algorithms in Memgraph MAGE modules.

## Table of Contents

1. [Memory Management](#memory-management)
2. [RAII and Resource Management](#raii-and-resource-management)
3. [Performance Optimization](#performance-optimization)
4. [Template Programming](#template-programming)
5. [Cache Efficiency](#cache-efficiency)
6. [Modern C++ Features](#modern-cpp-features)
7. [Graph Algorithm Patterns](#graph-algorithm-patterns)
8. [Memgraph MAGE Specific](#memgraph-mage-specific)

## Memory Management

### Core Principles

1. **Ownership Clarity** (Google C++ Style Guide)
   - Keep ownership with the code that allocated it
   - Use smart pointers to make ownership explicit and self-documenting
   - Prefer `std::unique_ptr` for single ownership
   - Use `std::shared_ptr` sparingly due to runtime overhead

2. **Pre-allocation for Performance** (Drake/Google)

   ```cpp
   // Good: Pre-allocate for performance-critical paths
   class GraphProcessor {
   private:
       std::vector<Node> node_buffer_;

   public:
       GraphProcessor(size_t expected_nodes) {
           node_buffer_.reserve(expected_nodes);
       }
   };
   ```

3. **Avoid Dynamic Allocation in Hot Paths**
   - Pre-allocate buffers before entering performance-critical loops
   - Use stack allocation or object pools for temporary objects
   - Consider `SmallVector` pattern for small, dynamic collections

### Memory Pooling Pattern

```cpp
template<typename T>
class MemoryPool {
private:
    std::vector<std::unique_ptr<T[]>> blocks_;
    std::vector<T*> free_list_;
    size_t block_size_;

public:
    explicit MemoryPool(size_t block_size = 1024)
        : block_size_(block_size) {
        allocate_block();
    }

    T* allocate() {
        if (free_list_.empty()) {
            allocate_block();
        }
        T* ptr = free_list_.back();
        free_list_.pop_back();
        return ptr;
    }

    void deallocate(T* ptr) {
        free_list_.push_back(ptr);
    }

private:
    void allocate_block() {
        auto block = std::make_unique<T[]>(block_size_);
        T* raw_block = block.get();
        blocks_.push_back(std::move(block));

        for (size_t i = 0; i < block_size_; ++i) {
            free_list_.push_back(&raw_block[i]);
        }
    }
};
```

## RAII and Resource Management

### C++ Core Guidelines Approach

1. **Resource Acquisition Is Initialization**

   ```cpp
   // Good: RAII for graph resources
   class GraphTransaction {
   private:
       MemgraphTxn* txn_;

   public:
       explicit GraphTransaction(MemgraphDb* db)
           : txn_(db->begin_transaction()) {
           if (!txn_) {
               throw std::runtime_error("Failed to begin transaction");
           }
       }

       ~GraphTransaction() {
           if (txn_) {
               txn_->rollback();  // Safe default
           }
       }

       void commit() {
           if (txn_) {
               txn_->commit();
               txn_ = nullptr;
           }
       }

       // Delete copy operations
       GraphTransaction(const GraphTransaction&) = delete;
       GraphTransaction& operator=(const GraphTransaction&) = delete;

       // Enable move operations
       GraphTransaction(GraphTransaction&& other) noexcept
           : txn_(std::exchange(other.txn_, nullptr)) {}

       GraphTransaction& operator=(GraphTransaction&& other) noexcept {
           if (this != &other) {
               if (txn_) txn_->rollback();
               txn_ = std::exchange(other.txn_, nullptr);
           }
           return *this;
       }
   };
   ```

2. **Exception Safety**
   - Use RAII for all resources (memory, locks, file handles, graph
     transactions)
   - Strong exception guarantee where possible
   - Basic exception guarantee as minimum

## Performance Optimization

### LLVM-Style Data Structures

1. **SmallVector Pattern**

   ```cpp
   template<typename T, size_t N>
   class SmallVector {
   private:
       alignas(T) char inline_storage_[N * sizeof(T)];
       T* data_ = reinterpret_cast<T*>(inline_storage_);
       size_t size_ = 0;
       size_t capacity_ = N;

   public:
       void push_back(T value) {
           if (size_ >= capacity_) {
               grow();
           }
           new(&data_[size_]) T(std::move(value));
           ++size_;
       }

   private:
       void grow() {
           size_t new_capacity = capacity_ * 2;
           T* new_data = static_cast<T*>(
               std::aligned_alloc(alignof(T), new_capacity * sizeof(T))
           );

           // Move existing elements
           for (size_t i = 0; i < size_; ++i) {
               new(&new_data[i]) T(std::move(data_[i]));
               data_[i].~T();
           }

           if (data_ != reinterpret_cast<T*>(inline_storage_)) {
               std::free(data_);
           }

           data_ = new_data;
           capacity_ = new_capacity;
       }
   };
   ```

2. **BitVector for Graph Properties**
   ```cpp
   class BitVector {
   private:
       std::vector<uint64_t> words_;
       size_t size_;

   public:
       void set(size_t idx) {
           size_t word_idx = idx / 64;
           size_t bit_idx = idx % 64;
           words_[word_idx] |= (1ULL << bit_idx);
       }

       bool test(size_t idx) const {
           size_t word_idx = idx / 64;
           size_t bit_idx = idx % 64;
           return words_[word_idx] & (1ULL << bit_idx);
       }

       // Efficient set operations
       BitVector& operator|=(const BitVector& other) {
           for (size_t i = 0; i < words_.size(); ++i) {
               words_[i] |= other.words_[i];
           }
           return *this;
       }
   };
   ```

### String and I/O Optimization

1. **Avoid std::iostream in Performance Code** (LLVM)

   ```cpp
   // Bad: std::cout has overhead
   std::cout << "Node " << node_id << " processed\n";

   // Good: Use LLVM-style raw_ostream or sprintf
   char buffer[256];
   snprintf(buffer, sizeof(buffer), "Node %lu processed\n", node_id);
   ```

2. **String Building**
   ```cpp
   // Good: Reserve capacity for string building
   std::string build_cypher_query(const std::vector<NodeId>& nodes) {
       std::string query;
       size_t estimated_size = nodes.size() * 20;  // Estimate
       query.reserve(estimated_size);

       query += "MATCH (n) WHERE n.id IN [";
       for (size_t i = 0; i < nodes.size(); ++i) {
           if (i > 0) query += ", ";
           query += std::to_string(nodes[i]);
       }
       query += "] RETURN n";

       return query;
   }
   ```

## Template Programming

### Modern C++ Template Best Practices

1. **Concepts (C++20) for Constraints**

   ```cpp
   template<typename T>
   concept GraphNode = requires(T t) {
       { t.id() } -> std::convertible_to<uint64_t>;
       { t.neighbors() } -> std::ranges::range;
   };

   template<GraphNode Node>
   class GraphAlgorithm {
   public:
       void process(const Node& node) {
           // Cleaner error messages with concepts
       }
   };
   ```

2. **Template Metaprogramming for Performance**

   ```cpp
   // Compile-time graph property calculations
   template<size_t N>
   struct GraphProperties {
       static constexpr size_t max_edges = N * (N - 1) / 2;
       static constexpr size_t cache_line_nodes = 64 / sizeof(Node);
   };

   // Expression templates for graph operations
   template<typename LHS, typename RHS, typename Op>
   class GraphExpression {
       const LHS& lhs_;
       const RHS& rhs_;

   public:
       GraphExpression(const LHS& lhs, const RHS& rhs)
           : lhs_(lhs), rhs_(rhs) {}

       auto evaluate() const {
           return Op::apply(lhs_.evaluate(), rhs_.evaluate());
       }
   };
   ```

3. **Fold Expressions (C++17) for Variadic Operations**
   ```cpp
   template<typename... Nodes>
   auto combine_node_properties(const Nodes&... nodes) {
       // Efficient compile-time expansion
       return (... + nodes.weight());
   }
   ```

## Cache Efficiency

### Cache-Friendly Data Structures

1. **Structure of Arrays (SoA) Pattern**

   ```cpp
   // Bad: Array of Structures (AoS) - poor cache locality
   struct Node {
       uint64_t id;
       double weight;
       uint32_t color;
       bool visited;
   };
   std::vector<Node> nodes;

   // Good: Structure of Arrays (SoA) - better cache locality
   struct GraphNodes {
       std::vector<uint64_t> ids;
       std::vector<double> weights;
       std::vector<uint32_t> colors;
       std::vector<bool> visited;

       size_t size() const { return ids.size(); }

       void reserve(size_t n) {
           ids.reserve(n);
           weights.reserve(n);
           colors.reserve(n);
           visited.reserve(n);
       }
   };
   ```

2. **Cache-Aligned Allocation**

   ```cpp
   template<typename T>
   class CacheAlignedVector {
   private:
       static constexpr size_t CACHE_LINE_SIZE = 64;
       T* data_ = nullptr;
       size_t size_ = 0;
       size_t capacity_ = 0;

   public:
       void reserve(size_t n) {
           size_t bytes = n * sizeof(T);
           size_t aligned_bytes =
               ((bytes + CACHE_LINE_SIZE - 1) / CACHE_LINE_SIZE)
               * CACHE_LINE_SIZE;

           data_ = static_cast<T*>(
               std::aligned_alloc(CACHE_LINE_SIZE, aligned_bytes)
           );
           capacity_ = aligned_bytes / sizeof(T);
       }
   };
   ```

3. **Prefetching for Graph Traversal**
   ```cpp
   void bfs_with_prefetch(const Graph& graph, NodeId start) {
       std::queue<NodeId> queue;
       BitVector visited(graph.num_nodes());

       queue.push(start);
       visited.set(start);

       while (!queue.empty()) {
           NodeId current = queue.front();
           queue.pop();

           const auto& neighbors = graph.neighbors(current);

           // Prefetch next level neighbors
           for (size_t i = 0; i < neighbors.size(); ++i) {
               if (i + 1 < neighbors.size()) {
                   __builtin_prefetch(&graph.node_data(neighbors[i + 1]), 0, 1);
               }

               if (!visited.test(neighbors[i])) {
                   visited.set(neighbors[i]);
                   queue.push(neighbors[i]);
               }
           }
       }
   }
   ```

## Modern C++ Features

### C++17/20 Best Practices

1. **Structured Bindings for Graph Iterations**

   ```cpp
   // C++17 structured bindings
   for (const auto& [node_id, properties] : graph.nodes()) {
       process_node(node_id, properties);
   }
   ```

2. **std::optional for Error Handling**

   ```cpp
   std::optional<Path> find_shortest_path(
       const Graph& graph,
       NodeId source,
       NodeId target
   ) {
       if (!graph.contains(source) || !graph.contains(target)) {
           return std::nullopt;
       }

       // Dijkstra's algorithm implementation
       Path result = dijkstra(graph, source, target);

       return result.is_valid() ? std::optional{result} : std::nullopt;
   }
   ```

3. **Ranges (C++20) for Graph Operations**
   ```cpp
   // Filter and transform graph nodes
   auto high_degree_nodes = graph.nodes()
       | std::views::filter([](const auto& node) {
           return node.degree() > 100;
       })
       | std::views::transform([](const auto& node) {
           return node.id();
       });
   ```

## Graph Algorithm Patterns

### High-Performance Graph Traversal

1. **Parallel BFS with Work Stealing**

   ```cpp
   class ParallelBFS {
   private:
       struct alignas(64) WorkQueue {
           std::vector<NodeId> current_level;
           std::vector<NodeId> next_level;
           std::atomic<size_t> current_pos{0};

           std::optional<NodeId> steal() {
               size_t pos = current_pos.fetch_add(1);
               return pos < current_level.size()
                   ? std::optional{current_level[pos]}
                   : std::nullopt;
           }
       };

   public:
       void search(const Graph& graph, NodeId start) {
           std::vector<WorkQueue> queues(std::thread::hardware_concurrency());
           BitVector visited(graph.num_nodes());

           queues[0].current_level.push_back(start);
           visited.set(start);

           #pragma omp parallel
           {
               int tid = omp_get_thread_num();

               while (any_work_available(queues)) {
                   // Try local queue first
                   if (auto node = queues[tid].steal()) {
                       process_node(graph, *node, visited, queues[tid].next_level);
                   } else {
                       // Work stealing from other queues
                       for (int i = 0; i < queues.size(); ++i) {
                           if (i != tid) {
                               if (auto node = queues[i].steal()) {
                                   process_node(graph, *node, visited,
                                              queues[tid].next_level);
                                   break;
                               }
                           }
                       }
                   }
               }

               #pragma omp barrier

               // Swap levels
               if (tid == 0) {
                   merge_next_levels(queues);
               }
           }
       }
   };
   ```

2. **Cache-Oblivious Graph Algorithms**
   ```cpp
   template<typename Graph>
   void recursive_graph_partition(
       const Graph& graph,
       NodeId* nodes,
       size_t start,
       size_t end,
       size_t threshold = 64  // Cache-friendly threshold
   ) {
       size_t size = end - start;

       if (size <= threshold) {
           // Base case: process in cache-friendly manner
           for (size_t i = start; i < end; ++i) {
               process_node_neighbors(graph, nodes[i]);
           }
           return;
       }

       // Recursive partitioning
       size_t mid = start + size / 2;

       // Process recursively
       recursive_graph_partition(graph, nodes, start, mid, threshold);
       recursive_graph_partition(graph, nodes, mid, end, threshold);
   }
   ```

## Memgraph MAGE Specific

### MAGE Module Best Practices

1. **Efficient Property Access**

   ```cpp
   // Memgraph C++ API usage
   void efficient_property_scan(mgp_graph* graph, mgp_memory* memory) {
       // Pre-allocate result storage
       auto* result = mgp::result_new_record(result_set);

       // Iterate efficiently through nodes
       for (auto node = mgp::graph_get_vertex_by_id(graph, 0);
            node.has_value();
            node = node->next()) {

           // Batch property access
           auto props = node->properties();

           // Process with minimal allocations
           if (auto weight = props.get("weight"); weight.has_value()) {
               process_weighted_node(node->id(), weight->as<double>());
           }
       }
   }
   ```

2. **Memory Management in MAGE**

   ```cpp
   class MageAlgorithm {
   private:
       mgp_memory* memory_;

       // Custom allocator using MAGE memory
       template<typename T>
       class MageAllocator {
           mgp_memory* mem_;
       public:
           T* allocate(size_t n) {
               return static_cast<T*>(
                   mgp_alloc(mem_, n * sizeof(T))
               );
           }

           void deallocate(T* p, size_t) {
               // MAGE handles deallocation automatically
           }
       };

   public:
       explicit MageAlgorithm(mgp_memory* mem) : memory_(mem) {}

       void run() {
           // Use MAGE allocator for STL containers
           std::vector<NodeId, MageAllocator<NodeId>>
               nodes(MageAllocator<NodeId>{memory_});

           // Algorithm implementation
       }
   };
   ```

3. **Subgraph Projections**
   ```cpp
   // Efficient subgraph handling
   class SubgraphProcessor {
   public:
       template<typename Predicate>
       void process_subgraph(
           mgp_graph* graph,
           Predicate node_filter,
           mgp_result* result
       ) {
           // Build subgraph index efficiently
           std::vector<NodeId> subgraph_nodes;
           subgraph_nodes.reserve(1000);  // Estimate

           // Single pass to identify subgraph
           for (auto node : graph->nodes()) {
               if (node_filter(node)) {
                   subgraph_nodes.push_back(node.id());
               }
           }

           // Process subgraph with optimized access pattern
           process_nodes_batch(subgraph_nodes, result);
       }
   };
   ```

## Summary

This style guide emphasizes:

1. **Memory Efficiency**: Pre-allocation, pooling, and RAII
2. **Cache Optimization**: Data layout, prefetching, and access patterns
3. **Modern C++ Features**: Concepts, ranges, and compile-time optimization
4. **Template Metaprogramming**: For zero-overhead abstractions
5. **Memgraph Integration**: Efficient use of MAGE APIs

Following these patterns will result in high-performance graph algorithms
suitable for production use in Memgraph MAGE modules.
