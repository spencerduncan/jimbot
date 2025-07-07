# JimBot: A Hybrid Machine Learning Architecture for Mastering Balatro

## Abstract

This document presents the machine learning architecture design for JimBot, an autonomous agent engineered to master the roguelike card game Balatro. The architecture combines reinforcement learning through Proximal Policy Optimization (PPO) with knowledge graph embeddings and selective large language model consultation to achieve superhuman gameplay. By integrating these complementary approaches, JimBot learns complex strategic patterns while maintaining computational efficiency and real-time decision-making capabilities.

## 1. Introduction

Balatro presents unique challenges for machine learning agents due to its combination of immediate tactical decisions and long-term strategic planning. The game requires players to balance scoring poker hands for immediate survival against building synergistic combinations of special cards (Jokers) that exponentially increase scoring potential. This dual optimization problem, combined with partial observability and a vast action space, necessitates a sophisticated learning architecture.

JimBot addresses these challenges through a novel hybrid approach that leverages the strengths of multiple machine learning paradigms. At its core, the system employs reinforcement learning to discover effective strategies through self-play. This learning is enhanced by a knowledge graph that captures and stores discovered synergies and strategic patterns, providing rich contextual features to the neural network. For particularly complex or novel situations, the system can consult a large language model to provide strategic reasoning and explore new possibilities.

## 2. Problem Formulation

### 2.1 The Balatro Learning Challenge

Mastering Balatro requires solving several interconnected problems simultaneously. The agent must learn to evaluate poker hands efficiently while also understanding the complex interactions between various Joker cards that modify scoring rules. These decisions must be made under uncertainty, as the agent cannot see future shop offerings or the order of cards in the deck.

The learning objective extends beyond simply winning individual runs. The agent must discover and exploit synergistic combinations of Jokers that enable exponential score scaling, adapt its strategy based on available resources and game progression, and balance the risk of pursuing long-term strategies against the immediate need to meet score requirements for each round.

### 2.2 Markov Decision Process Formulation

We model Balatro as a Markov Decision Process (MDP) with the following components:

The state space encompasses all relevant game information, including the current hand of cards, owned Jokers and their properties, game progression indicators (ante, round, score requirements), available resources (money, hands, discards), and the current game phase. This high-dimensional state space is augmented with strategic features extracted from the knowledge graph, providing historical context about successful strategies and synergies.

The action space varies by game phase but includes approximately 1000 discrete actions. During the playing phase, the agent can choose which cards to play or discard from the current hand. In the shop phase, actions include purchasing Jokers, buying booster packs, selling owned Jokers, rerolling the shop, or skipping to the next round. The blind selection phase offers choices between different difficulty levels and associated rewards.

The reward structure is carefully designed to encourage both immediate performance and long-term strategic thinking. Immediate rewards are granted for score gains and successful round completion, with larger bonuses for completing antes (sets of three rounds). Terminal rewards strongly incentivize winning runs while penalizing failures. Additionally, shaping rewards encourage the discovery and exploitation of synergistic Joker combinations.

## 3. Neural Network Architecture

### 3.1 BalatroNet Design Philosophy

The neural network architecture, termed BalatroNet, is designed to process the multimodal nature of Balatro's state space efficiently. Rather than treating all inputs uniformly, the network employs specialized encoders for different aspects of the game state, allowing each component to learn appropriate representations for its domain.

The architecture consists of three primary encoding pathways that process cards, Jokers, and game state information separately before combining them through a fusion network. This separation allows each encoder to specialize in extracting relevant features from its input domain while the fusion network learns to integrate these diverse information sources for decision-making.

### 3.2 Component Architecture Details

The card encoder processes information about the 52-card deck, including each card's suit, rank, enhancement status, and current location (hand, deck, or discarded). This encoder utilizes convolutional layers to capture local patterns in card combinations, particularly important for identifying potential poker hands. The output is a 128-dimensional representation that captures both the current hand's immediate scoring potential and the deck's overall composition.

The Joker encoder is more complex, handling up to 150 different Joker types with varying effects and synergies. This component employs multi-head attention mechanisms to model the interactions between owned Jokers explicitly. Each Joker is first embedded based on its properties (rarity, cost, effect type), then the attention mechanism learns to identify synergistic combinations. The attention weights provide interpretable insights into which Joker combinations the network considers important, outputting a 256-dimensional representation.

The state encoder processes scalar game information such as current ante, available money, hands remaining, and score requirements. This component uses standard fully connected layers with layer normalization to ensure stable gradients across the wide range of input scales. The resulting 64-dimensional encoding captures the current game context and urgency level.

### 3.3 Fusion and Decision Networks

The fusion network combines the outputs from all encoders along with the 128-dimensional strategic embedding from the knowledge graph. This creates a 576-dimensional representation that undergoes further processing through two hidden layers with 512 units each. The network employs residual connections and dropout for regularization, ensuring robust learning even with limited data in early training phases.

The final layer splits into two heads: a policy head that outputs action probabilities and a value head that estimates the expected return from the current state. The policy head incorporates an action masking mechanism that sets invalid action probabilities to zero, ensuring the agent only considers legal moves. This masking is crucial for efficient exploration, as it prevents the agent from wasting time learning that invalid actions yield no reward.

## 4. Reinforcement Learning Framework

### 4.1 Proximal Policy Optimization

JimBot employs Proximal Policy Optimization (PPO) as its core reinforcement learning algorithm. PPO is particularly well-suited for this application due to its sample efficiency in high-dimensional state spaces and its stability during training. The algorithm's conservative policy updates prevent catastrophic forgetting of successful strategies while still allowing for continuous improvement.

The PPO implementation uses carefully tuned hyperparameters to balance exploration and exploitation. The clipping parameter of 0.2 prevents overly aggressive policy updates, while an entropy coefficient of 0.01 encourages sufficient exploration to discover novel strategies. The algorithm uses Generalized Advantage Estimation (GAE) with λ=0.95 to balance bias and variance in advantage estimates, crucial for learning from delayed rewards in Balatro's long game sessions.

### 4.2 Training Dynamics

Training proceeds through iterative cycles of data collection and policy improvement. During each iteration, multiple parallel environments collect gameplay trajectories using the current policy. These environments run asynchronously, allowing for efficient utilization of computational resources while gathering diverse experiences.

The collected trajectories undergo advantage estimation using GAE, which helps attribute rewards to the appropriate actions even when outcomes are delayed. The policy then updates through multiple epochs of minibatch gradient descent, with each update carefully constrained by PPO's clipping mechanism to ensure stable learning progression.

Every few iterations, successful trajectories are analyzed to extract strategic patterns and update the knowledge graph. This creates a positive feedback loop where discovered strategies enhance future decision-making through improved feature representations. The system maintains checkpoints of the best-performing policies, allowing for recovery from potential training instabilities and enabling ensemble approaches during deployment.

## 5. Knowledge Graph Integration

### 5.1 Strategic Knowledge Representation

The knowledge graph, implemented in Memgraph, serves as the system's long-term strategic memory. It stores discovered relationships between game elements, successful strategic patterns, and historical performance data in a queryable format that provides real-time strategic context to the neural network.

The graph schema centers around four primary node types: Jokers, Strategies, Cards, and GameStates. Jokers are represented with their full property sets and learned embeddings. Strategies capture high-level gameplay patterns such as "flush building" or "multiplicative scaling." Cards maintain their basic properties and enhancement states. GameStates store snapshots of critical decision points for future analysis.

Relationships in the graph capture the rich interactions between these elements. SYNERGIZES_WITH relationships between Jokers include strength scores, confidence levels based on sample size, and contextual information about when synergies are most effective. ENABLES_STRATEGY relationships link Jokers to the high-level strategies they support, while REQUIRES_CARD relationships indicate specific card dependencies for Joker activation.

### 5.2 Feature Extraction Pipeline

During gameplay, the knowledge graph provides strategic features through an efficient extraction pipeline. For each game state, the system queries the graph to obtain relevant strategic information, which is then encoded into a fixed-size feature vector for neural network consumption.

The extraction process computes several categories of features. Synergy features aggregate the pairwise synergy strengths between currently owned Jokers, providing statistics such as mean, maximum, and variance of synergy scores. Strategy alignment features identify which high-level strategies are enabled by the current Joker configuration and their historical success rates. Victory path features analyze potential future Joker purchases within budget constraints, identifying the most promising additions to the current setup.

These queries are optimized for sub-50ms response times through careful indexing and caching strategies. Frequently accessed synergy scores are materialized and updated incrementally, while complex path-finding queries use approximation algorithms that trade small accuracy losses for significant speed improvements.

## 6. Large Language Model Integration

### 6.1 Strategic Consultation Framework

While the core learning occurs through reinforcement learning, JimBot incorporates large language model consultation for handling novel situations and providing strategic reasoning. This integration is carefully designed to enhance exploration and decision-making in complex scenarios while maintaining cost efficiency through aggressive rate limiting and caching.

The LLM consultation system operates asynchronously, preventing any impact on real-time decision-making. When the neural network exhibits high uncertainty (measured through policy entropy) or faces particularly complex decisions (such as late-game scenarios with multiple synergistic Jokers), the system queues a consultation request. These requests are batched and processed during natural pauses in gameplay, such as between rounds.

The consultation process provides two primary benefits: strategic advice for immediate decisions and meta-analysis of failed runs to identify missing patterns or strategies. The strategic advice includes specific action recommendations with confidence scores and explanations, helping the system understand why certain choices are preferable. Meta-analysis examines patterns across multiple failed runs to identify systematic errors or missed opportunities, generating insights that update the knowledge graph for future improvement.

### 6.2 Cost Optimization Strategies

Given the computational cost of LLM queries, the system employs multiple optimization strategies to maintain operations within a budget of 100 consultations per hour. A three-tier caching system stores exact query matches, semantically similar queries (using embedding similarity), and abstracted strategic patterns. This caching achieves hit rates exceeding 85% for common scenarios.

The system prioritizes consultations based on decision importance and uncertainty levels. High-stakes decisions, such as boss blind selections or complex multi-Joker synergy evaluations, receive priority for LLM consultation. Lower-priority queries fall back to cached responses or heuristic strategies derived from the knowledge graph.

Batch processing further improves efficiency by combining multiple related queries into single LLM calls. Post-game analysis aggregates entire game histories for comprehensive strategic review, extracting multiple insights from a single consultation. These insights are immediately incorporated into the knowledge graph, ensuring that each LLM consultation provides lasting value to the system.

## 7. Learning Dynamics and Continuous Improvement

### 7.1 Phased Learning Approach

JimBot's training follows a structured progression through distinct learning phases, each optimized for different aspects of strategy discovery and refinement. This phased approach ensures efficient exploration of the strategy space while progressively focusing on the most promising approaches.

The initial exploration phase emphasizes diversity in action selection through increased entropy bonuses and frequent LLM consultation. During this phase, the system actively seeks novel Joker combinations and strategic approaches, rapidly populating the knowledge graph with discovered patterns. The neural network learns basic game mechanics and develops initial value estimates for different game states.

As training progresses into the exploitation phase, the system begins to converge on successful strategies. Entropy bonuses are reduced, causing the policy to become more deterministic in favorable situations while maintaining exploration in uncertain states. LLM consultation frequency decreases as the knowledge graph provides increasingly comprehensive strategic guidance. The system refines its understanding of synergies and begins to develop sophisticated multi-Joker strategies.

The final optimization phase focuses on perfecting execution of discovered strategies. The policy becomes highly specialized, with minimal exploration except in genuinely novel situations. LLM consultation drops below 5% of decisions, reserved only for unprecedented game states or periodic meta-analysis. The knowledge graph undergoes pruning to remove low-confidence relationships and consolidate redundant patterns.

### 7.2 Meta-Learning and Adaptation

Beyond learning individual strategies, JimBot incorporates meta-learning components that monitor and guide the overall learning process. These components track learning efficiency metrics, identify when performance plateaus occur, and automatically adjust training parameters to maintain progress.

The meta-learning system monitors several key indicators of learning health. Strategy discovery rate tracks how frequently new synergistic combinations are identified, with declining rates triggering increased exploration. Performance trajectory analysis identifies stagnation in win rates or score improvements, automatically adjusting difficulty targets or exploration parameters. Knowledge graph growth patterns reveal whether the system is discovering genuinely new strategies or merely refining existing ones.

When learning plateaus are detected, the system employs several intervention strategies. Curriculum learning adjustments modify the difficulty progression, potentially revisiting earlier antes with new strategic knowledge. Exploration bonuses temporarily increase entropy coefficients to encourage deviation from established patterns. Targeted LLM consultations request specific analysis of recent failures to identify systematic blind spots in the current policy.

## 8. Implementation Considerations

### 8.1 Computational Efficiency

Achieving real-time performance requires careful optimization across all system components. The neural network inference must complete within 50ms to maintain smooth gameplay, necessitating efficient model architectures and optimized deployment strategies.

The system employs several optimization techniques to meet performance requirements. Vectorized environment implementations allow parallel simulation of multiple games, maximizing throughput during training. The neural network uses mixed precision training to accelerate computation while maintaining numerical stability. Knowledge graph queries are aggressively cached and use approximate algorithms where exact solutions would be too slow.

Action masking is implemented using sparse tensor operations to efficiently handle the large but mostly invalid action space. The mask computation is cached when possible and updated incrementally as game state changes. This approach reduces the computational overhead of maintaining valid action sets while ensuring the agent never attempts illegal moves.

### 8.2 Memory Management

Operating within memory constraints requires careful management of the various system components. The knowledge graph, while providing valuable strategic context, must balance comprehensive coverage with storage limitations. The system implements several strategies to maintain memory efficiency while preserving essential strategic knowledge.

Periodic pruning removes low-value information from the knowledge graph, including game states older than a threshold without associated critical decisions, synergy relationships with insufficient statistical support, and redundant strategy patterns that can be derived from more general rules. This pruning occurs during natural training breaks to avoid impacting real-time performance.

Experience replay buffers use prioritized sampling to maintain only the most valuable trajectories. Priority is determined by factors including trajectory return variance (indicating interesting or unusual games), strategic novelty (games featuring rare Joker combinations), and learning potential (games with high temporal difference errors). This approach ensures that limited memory is used for the most educational experiences.

## 9. Evaluation and Metrics

### 9.1 Performance Metrics

Evaluating JimBot's performance requires multiple metrics that capture different aspects of Balatro mastery. Win rate provides a basic measure of success but fails to capture the quality of play or strategic sophistication. Therefore, the system tracks a comprehensive suite of metrics.

Primary performance metrics include win rate at various difficulty levels, average final score across winning runs, consistency measured by score variance, and rate of achieving specific strategic milestones (such as assembling particular synergistic combinations). The system also tracks learning efficiency metrics such as sample efficiency (games required to achieve performance levels), strategy discovery rate, and knowledge graph growth patterns.

Strategic quality metrics evaluate the sophistication of discovered strategies. These include synergy exploitation efficiency (how well the agent utilizes discovered combinations), adaptation speed to new game situations, and diversity of successful strategic approaches. These metrics help ensure that JimBot develops flexible, robust strategies rather than overspecializing in narrow approaches.

### 9.2 Ablation Studies

Understanding the contribution of each system component requires systematic ablation studies. These experiments isolate individual components to measure their impact on overall performance. Key ablations include training without knowledge graph features to measure the value of strategic context, disabling LLM consultation to evaluate its contribution to exploration and strategy discovery, and using simplified reward structures to understand the importance of reward shaping.

Results from these ablations inform system optimization and highlight critical dependencies. For example, preliminary experiments suggest that the knowledge graph provides approximately 30% improvement in sample efficiency, while LLM consultation, despite being used sparingly, contributes significantly to discovering non-obvious strategies that pure reinforcement learning might miss.

## 10. Future Directions

### 10.1 Architectural Extensions

Several promising extensions could further enhance JimBot's capabilities. Hierarchical reinforcement learning could decompose the complex decision-making into strategic and tactical levels, potentially improving long-term planning. Option discovery frameworks could automatically identify and learn reusable strategic patterns, creating a library of strategic "options" that simplify decision-making in common situations.

Model-based components could enhance sample efficiency by learning to predict game state transitions, allowing for planning and strategy evaluation without extensive real-world trials. This would be particularly valuable for evaluating rare or expensive strategic choices that occur infrequently in normal play.

### 10.2 Transfer Learning Opportunities

The strategic knowledge captured in JimBot's architecture may transfer to related domains. The knowledge graph structure and strategic reasoning patterns could apply to other roguelike games with synergistic mechanics. The hybrid architecture combining reinforcement learning with knowledge graphs and LLM consultation could serve as a template for tackling other complex strategic domains where pure reinforcement learning struggles with exploration or strategic reasoning.

## 11. Conclusion

JimBot represents a sophisticated approach to mastering complex strategic games through hybrid machine learning architectures. By combining reinforcement learning's ability to optimize through experience, knowledge graphs' capacity for storing and retrieving strategic patterns, and large language models' reasoning capabilities, the system achieves robust performance while maintaining computational efficiency.

The architecture's key innovation lies in its seamless integration of these complementary approaches. The reinforcement learning core provides the primary decision-making capability, while the knowledge graph enriches every decision with historical strategic context. Large language model consultation, used judiciously, enables exploration of novel strategies and provides meta-level insights that improve long-term learning efficiency.

This design demonstrates that complex strategic games need not require brute-force computational approaches. Instead, by leveraging the strengths of different AI technologies in concert, it is possible to create systems that learn efficiently, play strategically, and continuously improve their performance. JimBot's architecture provides a blueprint for tackling similar challenges in other domains where strategic reasoning, pattern recognition, and adaptive learning converge.