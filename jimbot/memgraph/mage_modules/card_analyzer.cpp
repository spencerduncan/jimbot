/**
 * @file card_analyzer.cpp
 * @brief MAGE module for high-performance card analysis in Balatro
 *
 * This module provides optimized algorithms for analyzing card combinations,
 * calculating hand strengths, and determining optimal card selections.
 */

#include <algorithm>
#include <chrono>
#include <cmath>
#include <string>
#include <unordered_map>
#include <vector>

#include <mgp.hpp>

extern "C" {
int mgp_init_module(mgp_module* module, mgp_memory* memory);
int mgp_shutdown_module();
}

namespace {

/**
 * Card representation for fast operations
 */
struct Card {
    std::string suit;
    std::string rank;
    std::string enhancement;
    int base_chips;

    int getRankValue() const {
        if (rank == "A")
            return 14;
        if (rank == "K")
            return 13;
        if (rank == "Q")
            return 12;
        if (rank == "J")
            return 11;
        return std::stoi(rank);
    }
};

/**
 * Hand evaluation result
 */
struct HandResult {
    std::string hand_type;
    int base_chips;
    int base_mult;
    std::vector<Card> scoring_cards;
    double strength_score;
};

/**
 * Fast hand evaluator using bit manipulation
 */
class HandEvaluator {
private:
    // Bit masks for suits
    static constexpr uint64_t SUIT_MASK = 0x1FFF;  // 13 bits for ranks

    uint64_t cardToBit(const Card& card) const {
        int rank_bit = card.getRankValue() - 2;  // 2-14 -> 0-12
        return 1ULL << rank_bit;
    }

    int countBits(uint64_t bits) const { return __builtin_popcountll(bits); }

public:
    HandResult evaluateHand(const std::vector<Card>& cards) {
        if (cards.size() < 5) {
            return {"Invalid", 0, 0, {}, 0.0};
        }

        // Build bit representations
        std::unordered_map<std::string, uint64_t> suit_bits;
        std::unordered_map<int, int> rank_counts;
        uint64_t all_ranks = 0;

        for (const auto& card : cards) {
            suit_bits[card.suit] |= cardToBit(card);
            rank_counts[card.getRankValue()]++;
            all_ranks |= cardToBit(card);
        }

        // Check for flush
        std::string flush_suit;
        for (const auto& [suit, bits] : suit_bits) {
            if (countBits(bits) >= 5) {
                flush_suit = suit;
                break;
            }
        }

        // Check for straights
        bool has_straight = false;
        uint64_t straight_mask = 0x1F;  // 5 consecutive bits
        for (int i = 0; i <= 9; ++i) {
            if ((all_ranks & (straight_mask << i)) == (straight_mask << i)) {
                has_straight = true;
                break;
            }
        }
        // Check A-2-3-4-5 straight
        if ((all_ranks & 0x100F) == 0x100F) {
            has_straight = true;
        }

        // Count pairs, trips, etc.
        std::vector<int> counts;
        for (const auto& [rank, count] : rank_counts) {
            if (count > 1) {
                counts.push_back(count);
            }
        }
        std::sort(counts.rbegin(), counts.rend());

        // Determine hand type
        HandResult result;

        if (!flush_suit.empty() && has_straight) {
            // Check if straight flush
            uint64_t flush_ranks = suit_bits[flush_suit];
            bool straight_flush = false;
            for (int i = 0; i <= 9; ++i) {
                if ((flush_ranks & (straight_mask << i)) == (straight_mask << i)) {
                    straight_flush = true;
                    break;
                }
            }
            if ((flush_ranks & 0x100F) == 0x100F) {
                straight_flush = true;
            }

            if (straight_flush) {
                result = {"Straight Flush", 100, 8, cards, 0.9};
            } else if (!counts.empty() && counts[0] == 3 && counts.size() > 1 && counts[1] == 2) {
                result = {"Flush House", 140, 14, cards, 0.95};
            } else {
                result = {"Flush", 35, 4, cards, 0.6};
            }
        } else if (!counts.empty() && counts[0] == 4) {
            result = {"Four of a Kind", 60, 7, cards, 0.8};
        } else if (!counts.empty() && counts[0] == 3 && counts.size() > 1 && counts[1] == 2) {
            result = {"Full House", 40, 4, cards, 0.65};
        } else if (!flush_suit.empty()) {
            result = {"Flush", 35, 4, cards, 0.6};
        } else if (has_straight) {
            result = {"Straight", 30, 4, cards, 0.55};
        } else if (!counts.empty() && counts[0] == 3) {
            result = {"Three of a Kind", 30, 3, cards, 0.5};
        } else if (counts.size() >= 2 && counts[0] == 2 && counts[1] == 2) {
            result = {"Two Pair", 20, 2, cards, 0.4};
        } else if (!counts.empty() && counts[0] == 2) {
            result = {"Pair", 10, 2, cards, 0.3};
        } else {
            result = {"High Card", 5, 1, cards, 0.1};
        }

        return result;
    }
};

/**
 * Joker effect calculator
 */
class JokerEffectCalculator {
public:
    struct JokerEffect {
        double chip_bonus;
        double mult_bonus;
        bool applies;
    };

    JokerEffect calculateEffect(const std::string& joker_name,
                                const Card& card,
                                const HandResult& hand) {
        JokerEffect effect{0.0, 0.0, false};

        // Suit-based jokers
        if (joker_name == "Greedy Joker" && card.suit == "Diamonds") {
            effect = {0.0, 3.0, true};
        } else if (joker_name == "Lusty Joker" && card.suit == "Hearts") {
            effect = {0.0, 3.0, true};
        } else if (joker_name == "Wrathful Joker" && card.suit == "Spades") {
            effect = {0.0, 3.0, true};
        } else if (joker_name == "Gluttonous Joker" && card.suit == "Clubs") {
            effect = {0.0, 3.0, true};
        }
        // Rank-based jokers
        else if (joker_name == "Fibonacci") {
            if (card.rank == "A" || card.rank == "2" || card.rank == "3" || card.rank == "5" ||
                card.rank == "8") {
                effect = {8.0, 0.0, true};
            }
        } else if (joker_name == "Even Steven") {
            int rank_val = card.getRankValue();
            if (rank_val % 2 == 0 && rank_val <= 10) {
                effect = {0.0, 4.0, true};
            }
        } else if (joker_name == "Odd Todd") {
            int rank_val = card.getRankValue();
            if (rank_val % 2 == 1 || rank_val > 10) {
                effect = {31.0, 0.0, true};
            }
        } else if (joker_name == "Scholar" && card.rank == "A") {
            effect = {20.0, 4.0, true};
        }

        return effect;
    }
};

}  // anonymous namespace

/**
 * Calculate the best possible hand from available cards
 */
void calculate_best_hand(mgp_list* args, mgp_graph* graph, mgp_result* result, mgp_memory* memory) {
    auto start_time = std::chrono::high_resolution_clock::now();

    // Parse input parameters
    if (mgp_list_size(args) < 1) {
        mgp_result_set_error_msg(result, "Missing required parameter: card_ids", memory);
        return;
    }

    mgp_value* card_list_val = mgp_list_at(args, 0);
    if (mgp_value_get_type(card_list_val) != MGP_VALUE_TYPE_LIST) {
        mgp_result_set_error_msg(result, "Parameter must be a list of card IDs", memory);
        return;
    }

    mgp_list* card_ids = mgp_value_get_list(card_list_val);
    size_t num_cards = mgp_list_size(card_ids);

    if (num_cards < 5) {
        mgp_result_set_error_msg(result, "Need at least 5 cards", memory);
        return;
    }

    // Fetch card data from graph
    std::vector<Card> cards;
    cards.reserve(num_cards);

    for (size_t i = 0; i < num_cards; ++i) {
        mgp_value* id_val = mgp_list_at(card_ids, i);
        if (mgp_value_get_type(id_val) != MGP_VALUE_TYPE_INT) {
            continue;
        }

        int64_t card_id = mgp_value_get_int(id_val);
        mgp_vertex* vertex = mgp_graph_get_vertex_by_id(graph, card_id, memory);

        if (!vertex)
            continue;

        // Extract card properties
        Card card;
        mgp_value* prop_val;

        if (mgp_vertex_get_property(vertex, "suit", memory, &prop_val) == MGP_ERROR_NO_ERROR) {
            card.suit = mgp_value_get_string(prop_val);
        }
        if (mgp_vertex_get_property(vertex, "rank", memory, &prop_val) == MGP_ERROR_NO_ERROR) {
            card.rank = mgp_value_get_string(prop_val);
        }
        if (mgp_vertex_get_property(vertex, "enhancement", memory, &prop_val) ==
            MGP_ERROR_NO_ERROR) {
            card.enhancement = mgp_value_get_string(prop_val);
        }
        if (mgp_vertex_get_property(vertex, "base_chips", memory, &prop_val) ==
            MGP_ERROR_NO_ERROR) {
            card.base_chips = mgp_value_get_int(prop_val);
        }

        cards.push_back(card);
    }

    // Find best 5-card combination
    HandEvaluator evaluator;
    HandResult best_hand;
    double best_score = -1.0;
    std::vector<size_t> best_indices;

    // Try all 5-card combinations
    if (cards.size() <= 10) {
        // Full enumeration for small sets
        std::vector<size_t> indices(cards.size());
        std::iota(indices.begin(), indices.end(), 0);

        do {
            std::vector<Card> hand;
            for (size_t i = 0; i < 5; ++i) {
                hand.push_back(cards[indices[i]]);
            }

            HandResult result = evaluator.evaluateHand(hand);
            double score =
                result.base_chips + result.base_mult * 50.0 + result.strength_score * 1000.0;

            if (score > best_score) {
                best_score = score;
                best_hand = result;
                best_indices = std::vector<size_t>(indices.begin(), indices.begin() + 5);
            }
        } while (std::next_permutation(indices.begin(), indices.begin() + 5));
    } else {
        // Heuristic for larger sets - prioritize high cards and suits
        // This is a simplified approach for performance
        std::sort(cards.begin(), cards.end(), [](const Card& a, const Card& b) {
            return a.getRankValue() > b.getRankValue();
        });

        std::vector<Card> hand(cards.begin(), cards.begin() + 5);
        best_hand = evaluator.evaluateHand(hand);
    }

    // Build result
    mgp_result_record* record = mgp_result_new_record(result);

    mgp_value* hand_type = mgp_value_make_string(best_hand.hand_type.c_str(), memory);
    mgp_result_record_insert(record, "hand_type", hand_type);

    mgp_value* chips = mgp_value_make_int(best_hand.base_chips, memory);
    mgp_result_record_insert(record, "base_chips", chips);

    mgp_value* mult = mgp_value_make_int(best_hand.base_mult, memory);
    mgp_result_record_insert(record, "base_mult", mult);

    mgp_value* strength = mgp_value_make_double(best_hand.strength_score, memory);
    mgp_result_record_insert(record, "strength_score", strength);

    // Add timing
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(
                        std::chrono::high_resolution_clock::now() - start_time)
                        .count();

    mgp_value* exec_time = mgp_value_make_int(duration, memory);
    mgp_result_record_insert(record, "execution_time_us", exec_time);
}

/**
 * Calculate total score with joker effects
 */
void calculate_score_with_jokers(mgp_list* args,
                                 mgp_graph* graph,
                                 mgp_result* result,
                                 mgp_memory* memory) {
    if (mgp_list_size(args) < 2) {
        mgp_result_set_error_msg(result, "Missing parameters: hand_cards, joker_names", memory);
        return;
    }

    // Parse hand cards
    mgp_value* cards_val = mgp_list_at(args, 0);
    mgp_list* card_list = mgp_value_get_list(cards_val);

    std::vector<Card> hand_cards;
    size_t num_cards = mgp_list_size(card_list);

    for (size_t i = 0; i < num_cards; ++i) {
        mgp_value* card_val = mgp_list_at(card_list, i);
        mgp_map* card_map = mgp_value_get_map(card_val);

        Card card;
        mgp_value* val;

        if (mgp_map_get(card_map, "suit", &val) == MGP_ERROR_NO_ERROR) {
            card.suit = mgp_value_get_string(val);
        }
        if (mgp_map_get(card_map, "rank", &val) == MGP_ERROR_NO_ERROR) {
            card.rank = mgp_value_get_string(val);
        }
        if (mgp_map_get(card_map, "enhancement", &val) == MGP_ERROR_NO_ERROR) {
            card.enhancement = mgp_value_get_string(val);
        }

        hand_cards.push_back(card);
    }

    // Parse joker names
    mgp_value* jokers_val = mgp_list_at(args, 1);
    mgp_list* joker_list = mgp_value_get_list(jokers_val);

    std::vector<std::string> joker_names;
    size_t num_jokers = mgp_list_size(joker_list);

    for (size_t i = 0; i < num_jokers; ++i) {
        mgp_value* name_val = mgp_list_at(joker_list, i);
        joker_names.push_back(mgp_value_get_string(name_val));
    }

    // Evaluate hand
    HandEvaluator evaluator;
    HandResult hand_result = evaluator.evaluateHand(hand_cards);

    // Calculate joker effects
    JokerEffectCalculator effect_calc;
    double total_chips = hand_result.base_chips;
    double total_mult = hand_result.base_mult;

    for (const auto& card : hand_result.scoring_cards) {
        double card_chips = card.base_chips;
        double card_mult = 0;

        // Apply joker effects
        for (const auto& joker_name : joker_names) {
            auto effect = effect_calc.calculateEffect(joker_name, card, hand_result);
            if (effect.applies) {
                card_chips += effect.chip_bonus;
                card_mult += effect.mult_bonus;
            }
        }

        total_chips += card_chips;
        total_mult += card_mult;
    }

    // Enhancement bonuses
    for (const auto& card : hand_result.scoring_cards) {
        if (card.enhancement == "bonus") {
            total_chips += 30;
        } else if (card.enhancement == "mult") {
            total_mult += 4;
        } else if (card.enhancement == "glass") {
            total_mult *= 2;
        } else if (card.enhancement == "steel") {
            total_mult *= 1.5;
        } else if (card.enhancement == "gold") {
            // Gold seal effect would be handled elsewhere
        }
    }

    double final_score = total_chips * total_mult;

    // Build result
    mgp_result_record* record = mgp_result_new_record(result);

    mgp_value* score = mgp_value_make_double(final_score, memory);
    mgp_result_record_insert(record, "total_score", score);

    mgp_value* chips = mgp_value_make_double(total_chips, memory);
    mgp_result_record_insert(record, "total_chips", chips);

    mgp_value* mult = mgp_value_make_double(total_mult, memory);
    mgp_result_record_insert(record, "total_mult", mult);
}

/**
 * Module initialization
 */
int mgp_init_module(mgp_module* module, mgp_memory* memory) {
    // Register calculate_best_hand function
    {
        mgp_proc* proc =
            mgp_module_add_read_procedure(module, "calculate_best_hand", calculate_best_hand);

        mgp_proc_add_arg(proc, "card_ids", mgp_type_list(mgp_type_any()));

        mgp_proc_add_result(proc, "hand_type", mgp_type_string());
        mgp_proc_add_result(proc, "base_chips", mgp_type_int());
        mgp_proc_add_result(proc, "base_mult", mgp_type_int());
        mgp_proc_add_result(proc, "strength_score", mgp_type_float());
        mgp_proc_add_result(proc, "execution_time_us", mgp_type_int());
    }

    // Register calculate_score_with_jokers function
    {
        mgp_proc* proc = mgp_module_add_read_procedure(
            module, "calculate_score_with_jokers", calculate_score_with_jokers);

        mgp_proc_add_arg(proc, "hand_cards", mgp_type_list(mgp_type_map()));
        mgp_proc_add_arg(proc, "joker_names", mgp_type_list(mgp_type_string()));

        mgp_proc_add_result(proc, "total_score", mgp_type_float());
        mgp_proc_add_result(proc, "total_chips", mgp_type_float());
        mgp_proc_add_result(proc, "total_mult", mgp_type_float());
    }

    return 0;
}

/**
 * Module shutdown
 */
int mgp_shutdown_module() {
    return 0;
}