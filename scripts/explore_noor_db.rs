use rusqlite::{Connection, Result};

fn main() -> Result<()> {
    let conn = Connection::open("C:\\Codex\\Kalima\\datasets\\NoorQuranMorphologyV1.0.db")?;

    // Get all table names
    println!("=== Tables in NoorQuranMorphologyV1.0.db ===\n");
    let mut stmt = conn.prepare("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")?;
    let tables = stmt.query_map([], |row| row.get::<_, String>(0))?;

    for table in tables {
        let table_name = table?;
        println!("Table: {}", table_name);

        // Get schema for each table
        let mut schema_stmt = conn.prepare(&format!("PRAGMA table_info({})", table_name))?;
        let columns = schema_stmt.query_map([], |row| {
            Ok(format!("  - {} ({})",
                row.get::<_, String>(1)?,  // column name
                row.get::<_, String>(2)?   // column type
            ))
        })?;

        for col in columns {
            println!("{}", col?);
        }

        // Get row count
        let count: i64 = conn.query_row(
            &format!("SELECT COUNT(*) FROM {}", table_name),
            [],
            |row| row.get(0)
        )?;
        println!("  Rows: {}\n", count);
    }

    // Sample some data from each table
    println!("\n=== Sample Data ===\n");

    let mut stmt = conn.prepare("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")?;
    let table_names: Vec<String> = stmt.query_map([], |row| row.get(0))?.collect::<Result<Vec<_>>>()?;

    for table_name in table_names {
        println!("Sample from {}:", table_name);
        let mut sample_stmt = conn.prepare(&format!("SELECT * FROM {} LIMIT 3", table_name))?;
        let column_count = sample_stmt.column_count();
        let column_names: Vec<String> = sample_stmt.column_names().iter().map(|s| s.to_string()).collect();

        let rows = sample_stmt.query_map([], |row| {
            let mut values = Vec::new();
            for i in 0..column_count {
                let val: Result<String> = row.get(i);
                values.push(val.unwrap_or_else(|_| "NULL".to_string()));
            }
            Ok(values)
        })?;

        println!("  Columns: {:?}", column_names);
        for (i, row) in rows.enumerate() {
            println!("  Row {}: {:?}", i + 1, row?);
        }
        println!();
    }

    Ok(())
}
