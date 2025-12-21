use rusqlite::{Connection, Result};

fn main() -> Result<()> {
    let conn = Connection::open("C:\\Codex\\Kalima\\data\\database\\kalima.db")?;

    println!("=== Current Kalima Database Schema ===\n");

    // Get all table names
    let mut stmt = conn.prepare("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")?;
    let tables = stmt.query_map([], |row| row.get::<_, String>(0))?;

    for table in tables {
        let table_name = table?;
        println!("\nTable: {}", table_name);

        // Get schema
        let mut schema_stmt = conn.prepare(&format!("PRAGMA table_info({})", table_name))?;
        let columns = schema_stmt.query_map([], |row| {
            Ok(format!("  {} {} {}",
                row.get::<_, String>(1)?,  // name
                row.get::<_, String>(2)?,  // type
                if row.get::<_, i32>(3)? == 1 { "NOT NULL" } else { "" }
            ))
        })?;

        for col in columns {
            println!("{}", col?);
        }

        // Row count
        let count: i64 = conn.query_row(
            &format!("SELECT COUNT(*) FROM {}", table_name),
            [],
            |row| row.get(0)
        )?;
        println!("  → {} rows", count);
    }

    // Check morphology table specifically
    println!("\n=== Sample Morphology Data ===");
    let mut morph_stmt = conn.prepare("SELECT * FROM morphology LIMIT 1")?;
    let column_names: Vec<String> = morph_stmt.column_names().iter().map(|s| s.to_string()).collect();
    println!("Morphology columns: {:?}", column_names);

    let mut rows = morph_stmt.query([])?;
    if let Some(row) = rows.next()? {
        println!("\nSample row:");
        for (i, name) in column_names.iter().enumerate() {
            let val: Result<String> = row.get(i);
            println!("  {}: {:?}", name, val.unwrap_or_else(|_| "NULL".to_string()));
        }
    }

    Ok(())
}
