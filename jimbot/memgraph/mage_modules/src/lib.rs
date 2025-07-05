//! Memgraph MAGE modules for high-performance graph algorithms in Rust
//!
//! This crate provides optimized algorithms for analyzing card combinations,
//! calculating hand strengths, and determining optimal card selections.

pub mod synergy_calculator;
pub mod victory_path_analyzer;

use std::os::raw::{c_char, c_int, c_void};

/// FFI wrapper for Memgraph module initialization
#[no_mangle]
pub extern "C" fn mgp_init_module(
    module: *mut c_void,
    memory: *mut c_void,
) -> c_int {
    // Register our Rust functions with Memgraph
    // This will be implemented when Rust MAGE bindings are available
    0 // Success
}

/// FFI wrapper for Memgraph module shutdown
#[no_mangle]
pub extern "C" fn mgp_shutdown_module() -> c_int {
    0 // Success
}