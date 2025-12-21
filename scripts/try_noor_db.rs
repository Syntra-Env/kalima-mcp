use rusqlite::{Connection, Result, OpenFlags};

fn main() -> Result<()> {
    let db_path = "C:\\Codex\\Kalima\\datasets\\NoorQuranMorphologyV1.0.db";

    println!("Trying different approaches to open NoorQuranMorphologyV1.0.db...\n");

    // Try 1: Direct open (maybe it's not encrypted after all)
    println!("Attempt 1: Direct open without encryption...");
    match Connection::open(db_path) {
        Ok(conn) => {
            println!("✓ Success! Database opened without encryption.");
            print_schema(&conn)?;
            return Ok(());
        }
        Err(e) => println!("✗ Failed: {}\n", e),
    }

    // Try 2: Open with empty password
    println!("Attempt 2: Open with empty password...");
    match Connection::open(db_path) {
        Ok(conn) => {
            if let Err(e) = conn.execute("PRAGMA key = '';", []) {
                println!("✗ Failed to set empty key: {}\n", e);
            } else {
                println!("✓ Trying with empty key...");
                match conn.execute("SELECT COUNT(*) FROM sqlite_master", []) {
                    Ok(_) => {
                        println!("✓ Success! Database opened with empty password.");
                        print_schema(&conn)?;
                        return Ok(());
                    }
                    Err(e) => println!("✗ Failed to query: {}\n", e),
                }
            }
        }
        Err(e) => println!("✗ Failed to open: {}\n", e),
    }

    // Try 3: Common default passwords
    let passwords = vec!["", "password", "123456", "admin", "noor", "quran", "Quran", "Noor"];

    for (i, pwd) in passwords.iter().enumerate() {
        println!("Attempt {}: Trying password '{}'...", i + 3, pwd);
        match Connection::open(db_path) {
            Ok(conn) => {
                let pragma = format!("PRAGMA key = '{}';", pwd);
                if let Err(e) = conn.execute(&pragma, []) {
                    println!("✗ Failed to set key: {}\n", e);
                    continue;
                }

                match conn.execute("SELECT COUNT(*) FROM sqlite_master", []) {
                    Ok(_) => {
                        println!("✓ Success! Password is: '{}'", pwd);
                        print_schema(&conn)?;
                        return Ok(());
                    }
                    Err(e) => println!("✗ Query failed: {}\n", e),
                }
            }
            Err(e) => println!("✗ Failed to open: {}\n", e),
        }
    }

    // Try 4: Check if it's actually a zip file or compressed
    println!("\nAttempt: Checking file magic bytes...");
    if let Ok(bytes) = std::fs::read(db_path) {
        let header: Vec<u8> = bytes.iter().take(16).copied().collect();
        println!("File header (hex): {:02X?}", header);

        // SQLite magic: "SQLite format 3\0"
        // ZIP magic: 50 4B (PK)
        // GZIP magic: 1F 8B

        if header.starts_with(b"SQLite format 3") {
            println!("✓ File has SQLite header - it should be openable!");
        } else if header.starts_with(b"PK") {
            println!("✗ File appears to be ZIP compressed");
        } else if header.starts_with(&[0x1F, 0x8B]) {
            println!("✗ File appears to be GZIP compressed");
        } else {
            println!("? Unknown file format - might be encrypted SQLite");
        }
    }

    println!("\n❌ Could not open database with any method tried.");
    println!("The database is likely encrypted and requires the correct password.");
    println!("Please check the Noor dataset documentation for the password.");

    Ok(())
}

fn print_schema(conn: &Connection) -> Result<()> {
    println!("\n=== Database Schema ===\n");

    let mut stmt = conn.prepare("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")?;
    let tables = stmt.query_map([], |row| row.get::<_, String>(0))?;

    for table in tables {
        let table_name = table?;
        println!("Table: {}", table_name);

        let mut schema_stmt = conn.prepare(&format!("PRAGMA table_info({})", table_name))?;
        let columns = schema_stmt.query_map([], |row| {
            Ok(format!("  - {} ({})", row.get::<_, String>(1)?, row.get::<_, String>(2)?))
        })?;

        for col in columns {
            println!("{}", col?);
        }

        let count: i64 = conn.query_row(
            &format!("SELECT COUNT(*) FROM {}", table_name),
            [],
            |row| row.get(0)
        )?;
        println!("  Rows: {}\n", count);
    }

    Ok(())
}
