use std::env;
use std::path::PathBuf;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // Get the directory containing Cargo.toml
    let cargo_dir = env::var("CARGO_MANIFEST_DIR").unwrap();
    let cargo_path = PathBuf::from(cargo_dir);
    
    // Navigate to jimbot/proto from the Cargo directory
    let proto_root = cargo_path
        .parent() // services/
        .unwrap()
        .parent() // work-tree-5/
        .unwrap()
        .join("jimbot")
        .join("proto");
    
    // Verify the proto files exist
    let balatro_proto = proto_root.join("balatro_events.proto");
    let resource_proto = proto_root.join("resource_coordinator.proto");
    
    if !balatro_proto.exists() {
        panic!("Proto file not found: {:?}", balatro_proto);
    }
    if !resource_proto.exists() {
        panic!("Proto file not found: {:?}", resource_proto);
    }
    
    // Tell cargo to recompile if proto files change
    println!("cargo:rerun-if-changed={}", balatro_proto.display());
    println!("cargo:rerun-if-changed={}", resource_proto.display());

    // Compile protocol buffers
    tonic_build::configure()
        .build_client(true)
        .build_server(true)
        .compile(
            &[
                balatro_proto.to_str().unwrap(),
                resource_proto.to_str().unwrap(),
            ],
            &[proto_root.to_str().unwrap()],
        )?;

    Ok(())
}