//! Performance benchmarks for the Balatro RNG system

use balatro_emulator::utils::{BalatroRng, PseudorandomState, SeedType};
use criterion::{black_box, criterion_group, criterion_main, Criterion};

fn benchmark_pseudoseed_generation(c: &mut Criterion) {
    let mut rng = BalatroRng::new(SeedType::String("BENCHMARK".to_string()));

    c.bench_function("pseudoseed_generation", |b| {
        let mut counter = 0;
        b.iter(|| {
            let key = format!("key_{counter}");
            let seed = rng.pseudoseed(black_box(&key));
            counter += 1;
            black_box(seed)
        })
    });
}

fn benchmark_pseudorandom_numeric(c: &mut Criterion) {
    let mut rng = BalatroRng::new(SeedType::String("BENCHMARK".to_string()));

    c.bench_function("pseudorandom_numeric", |b| {
        let mut counter = 0;
        b.iter(|| {
            let seed = SeedType::Numeric(counter);
            let value = rng.pseudorandom(black_box(seed), Some(1), Some(100));
            counter += 1;
            black_box(value)
        })
    });
}

fn benchmark_pseudorandom_string(c: &mut Criterion) {
    let mut rng = BalatroRng::new(SeedType::String("BENCHMARK".to_string()));

    c.bench_function("pseudorandom_string", |b| {
        let mut counter = 0;
        b.iter(|| {
            let seed = SeedType::String(format!("seed_{counter}"));
            let value = rng.pseudorandom(black_box(seed), Some(1), Some(100));
            counter += 1;
            black_box(value)
        })
    });
}

fn benchmark_pseudoshuffle(c: &mut Criterion) {
    let mut rng = BalatroRng::new(SeedType::String("BENCHMARK".to_string()));

    c.bench_function("pseudoshuffle_deck", |b| {
        let mut counter = 0;
        b.iter(|| {
            let mut deck: Vec<u32> = (1..=52).collect();
            rng.pseudoshuffle(black_box(&mut deck), counter);
            counter += 1;
            black_box(deck)
        })
    });
}

fn benchmark_pseudorandom_element(c: &mut Criterion) {
    let mut rng = BalatroRng::new(SeedType::String("BENCHMARK".to_string()));
    let collection = vec![
        "item1", "item2", "item3", "item4", "item5", "item6", "item7", "item8", "item9", "item10",
    ];

    c.bench_function("pseudorandom_element", |b| {
        let mut counter = 0;
        b.iter(|| {
            let element = rng.pseudorandom_element(black_box(&collection), counter);
            counter += 1;
            black_box(element)
        })
    });
}

fn benchmark_weighted_choice(c: &mut Criterion) {
    let mut rng = BalatroRng::new(SeedType::String("BENCHMARK".to_string()));
    let choices = vec![
        ("common", 70.0),
        ("uncommon", 20.0),
        ("rare", 8.0),
        ("epic", 1.8),
        ("legendary", 0.2),
    ];

    c.bench_function("weighted_choice", |b| {
        let mut counter = 0;
        b.iter(|| {
            let choice = rng.weighted_choice(black_box(&choices), counter);
            counter += 1;
            black_box(choice)
        })
    });
}

fn benchmark_probability_check(c: &mut Criterion) {
    let mut rng = BalatroRng::new(SeedType::String("BENCHMARK".to_string()));

    c.bench_function("probability_check", |b| {
        let mut counter = 0;
        b.iter(|| {
            let result = rng.probability_check(black_box(0.5), counter);
            counter += 1;
            black_box(result)
        })
    });
}

fn benchmark_card_rng_generation(c: &mut Criterion) {
    let mut rng = BalatroRng::new(SeedType::String("BENCHMARK".to_string()));

    c.bench_function("card_rng_generation", |b| {
        let mut counter = 0;
        b.iter(|| {
            let ante = (counter % 8) + 1;
            let seed = rng.get_card_rng(black_box("rarity"), ante as u8, Some("joker"));
            counter += 1;
            black_box(seed)
        })
    });
}

fn benchmark_shop_rng_generation(c: &mut Criterion) {
    let mut rng = BalatroRng::new(SeedType::String("BENCHMARK".to_string()));

    c.bench_function("shop_rng_generation", |b| {
        let mut counter = 0;
        b.iter(|| {
            let ante = (counter % 8) + 1;
            let reroll = counter % 10;
            let seed = rng.get_shop_rng(black_box(ante as u8), black_box(reroll as u32));
            counter += 1;
            black_box(seed)
        })
    });
}

fn benchmark_joker_rng_generation(c: &mut Criterion) {
    let mut rng = BalatroRng::new(SeedType::String("BENCHMARK".to_string()));

    c.bench_function("joker_rng_generation", |b| {
        let mut counter = 0;
        b.iter(|| {
            let joker_id = format!("joker_{}", counter % 100);
            let trigger = counter % 20;
            let seed = rng.get_joker_rng(black_box(&joker_id), black_box(trigger as u32));
            counter += 1;
            black_box(seed)
        })
    });
}

fn benchmark_state_serialization(c: &mut Criterion) {
    let mut rng = BalatroRng::new(SeedType::String("BENCHMARK".to_string()));

    // Populate the state with some data
    for i in 0..100 {
        rng.pseudoseed(&format!("key_{i}"));
    }

    c.bench_function("state_serialization", |b| {
        b.iter(|| {
            let state = rng.state();
            let serialized = serde_json::to_string(black_box(state)).unwrap();
            black_box(serialized)
        })
    });
}

fn benchmark_state_deserialization(c: &mut Criterion) {
    let mut rng = BalatroRng::new(SeedType::String("BENCHMARK".to_string()));

    // Populate the state with some data
    for i in 0..100 {
        rng.pseudoseed(&format!("key_{i}"));
    }

    let state = rng.state();
    let serialized = serde_json::to_string(state).unwrap();

    c.bench_function("state_deserialization", |b| {
        b.iter(|| {
            let deserialized: PseudorandomState =
                serde_json::from_str(black_box(&serialized)).unwrap();
            black_box(deserialized)
        })
    });
}

fn benchmark_game_simulation(c: &mut Criterion) {
    c.bench_function("game_simulation_1000_operations", |b| {
        b.iter(|| {
            let mut rng = BalatroRng::new(SeedType::String("GAME_SIM".to_string()));

            // Simulate 1000 game operations
            for i in 0..1000 {
                // Card operations
                let card_seed = rng.get_card_rng("rarity", ((i % 8) + 1) as u8, Some("joker"));
                let _card_value =
                    rng.pseudorandom(SeedType::Numeric(card_seed), Some(1), Some(100));

                // Shop operations
                let shop_seed = rng.get_shop_rng(((i % 8) + 1) as u8, (i % 5) as u32);
                let _shop_check = rng.probability_check(0.3, shop_seed);

                // Joker operations
                let joker_seed = rng.get_joker_rng(&format!("joker_{}", i % 20), (i % 10) as u32);
                let _joker_effect =
                    rng.pseudorandom(SeedType::Numeric(joker_seed), Some(1), Some(50));
            }

            black_box(rng)
        })
    });
}

criterion_group!(
    benches,
    benchmark_pseudoseed_generation,
    benchmark_pseudorandom_numeric,
    benchmark_pseudorandom_string,
    benchmark_pseudoshuffle,
    benchmark_pseudorandom_element,
    benchmark_weighted_choice,
    benchmark_probability_check,
    benchmark_card_rng_generation,
    benchmark_shop_rng_generation,
    benchmark_joker_rng_generation,
    benchmark_state_serialization,
    benchmark_state_deserialization,
    benchmark_game_simulation
);

criterion_main!(benches);
