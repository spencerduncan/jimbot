use std::env;
use std::path::{Path, PathBuf};

fn find_proto_root(cargo_path: &Path) -> PathBuf {
    // Strategy 1: Check if we're in a Docker CI environment
    if env::var("CI").is_ok() || env::var("DOCKER_CI").is_ok() {
        // In CI, proto files might be at /workspace/jimbot/proto
        let ci_proto_path = PathBuf::from("/workspace/jimbot/proto");
        if ci_proto_path.exists() {
            return ci_proto_path;
        }
    }

    // Strategy 2: Look for jimbot/proto relative to current directory
    let mut current = cargo_path.to_path_buf();
    while let Some(parent) = current.parent() {
        let proto_path = parent.join("jimbot").join("proto");
        if proto_path.exists() {
            return proto_path;
        }
        current = parent.to_path_buf();
    }

    // Strategy 3: Original relative path (for local development)
    cargo_path
        .parent() // services/
        .unwrap()
        .parent() // project root
        .unwrap()
        .join("jimbot")
        .join("proto")
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Get the directory containing Cargo.toml
    let cargo_dir = env::var("CARGO_MANIFEST_DIR").unwrap();
    let cargo_path = PathBuf::from(cargo_dir);

    // Try multiple strategies to find the proto files
    let proto_root = find_proto_root(&cargo_path);
    
    // Debug output
    eprintln!("build.rs: CARGO_MANIFEST_DIR = {}", cargo_path.display());
    eprintln!("build.rs: Proto root = {}", proto_root.display());
    eprintln!("build.rs: CI env var = {:?}", env::var("CI").ok());

    // Verify the proto files exist
    let balatro_proto = proto_root.join("balatro_events.proto");
    let resource_proto = proto_root.join("resource_coordinator.proto");

    if !balatro_proto.exists() {
        eprintln!("build.rs: Looking for proto file at: {}", balatro_proto.display());
        eprintln!("build.rs: Current directory contents:");
        if let Ok(entries) = std::fs::read_dir(&proto_root) {
            for entry in entries {
                if let Ok(entry) = entry {
                    eprintln!("  - {}", entry.path().display());
                }
            }
        }
        panic!("Proto file not found: {balatro_proto:?}");
    }
    if !resource_proto.exists() {
        panic!("Proto file not found: {resource_proto:?}");
    }

    // Tell cargo to recompile if proto files change
    println!("cargo:rerun-if-changed={}", balatro_proto.display());
    println!("cargo:rerun-if-changed={}", resource_proto.display());

    // Compile protocol buffers
    tonic_build::configure()
        .build_client(true)
        .build_server(true)
        // Disable clippy warnings for generated code
        .emit_rerun_if_changed(false)
        .compile(
            &[
                balatro_proto.to_str().unwrap(),
                resource_proto.to_str().unwrap(),
            ],
            &[proto_root.to_str().unwrap()],
        )?;

    Ok(())
}
