// Simple program to initialize the database with schema migrations
use store::SqliteStorage;

#[tokio::main]
async fn main() {
    let db_path = r"C:\Codex\Kalima\data\database\kalima.db";
    println!("Connecting to {}...", db_path);

    match SqliteStorage::connect(db_path).await {
        Ok(_) => println!("✓ Database initialized successfully!"),
        Err(e) => eprintln!("✗ Error: {}", e),
    }

    println!("\nNew tables should now exist:");
    println!("  - patterns");
    println!("  - claims");
    println!("  - claim_evidence");
    println!("  - claim_dependencies");
}
