use std::fs;
use std::io::Read;

fn main() {
    let db_path = "C:\\Codex\\Kalima\\datasets\\NoorQuranMorphologyV1.0.db";

    println!("Analyzing NoorQuranMorphologyV1.0.db...\n");

    // Check file size
    match fs::metadata(db_path) {
        Ok(metadata) => {
            println!("File size: {} bytes ({:.2} MB)", metadata.len(), metadata.len() as f64 / 1_048_576.0);
        }
        Err(e) => {
            println!("Cannot read file metadata: {}", e);
            return;
        }
    }

    // Read first 100 bytes
    match fs::File::open(db_path) {
        Ok(mut file) => {
            let mut buffer = vec![0u8; 100];
            match file.read(&mut buffer) {
                Ok(n) => {
                    println!("\nFirst {} bytes (hex):", n);
                    for (i, chunk) in buffer[..n].chunks(16).enumerate() {
                        print!("{:04x}: ", i * 16);
                        for byte in chunk {
                            print!("{:02x} ", byte);
                        }
                        print!("  ");
                        for byte in chunk {
                            if *byte >= 32 && *byte < 127 {
                                print!("{}", *byte as char);
                            } else {
                                print!(".");
                            }
                        }
                        println!();
                    }

                    // Check for known signatures
                    println!("\nFile type analysis:");
                    if buffer.starts_with(b"SQLite format 3") {
                        println!("✓ Standard SQLite database");
                    } else if buffer.starts_with(b"PK") {
                        println!("✗ ZIP archive - needs extraction");
                    } else if buffer.starts_with(&[0x1F, 0x8B]) {
                        println!("✗ GZIP compressed");
                    } else if buffer[0..4] == [0x55, 0x56, 0x47, 0x19] {
                        println!("? Possibly encrypted/compressed with custom format");
                    } else {
                        println!("? Unknown format");
                        println!("  First 4 bytes: {:02X} {:02X} {:02X} {:02X}",
                                 buffer[0], buffer[1], buffer[2], buffer[3]);
                    }
                }
                Err(e) => println!("Cannot read file: {}", e),
            }
        }
        Err(e) => println!("Cannot open file: {}", e),
    }

    // Check if the ZIP contains the real database
    println!("\nChecking extracted database from ZIP...");
    let extracted_path = "C:\\Codex\\Kalima\\datasets\\Noor dataset\\NoorQuranMorphologyV1.0.db";

    match fs::File::open(extracted_path) {
        Ok(mut file) => {
            let mut buffer = vec![0u8; 16];
            match file.read(&mut buffer) {
                Ok(n) => {
                    print!("Extracted file header: ");
                    for byte in &buffer[..n] {
                        print!("{:02x} ", byte);
                    }
                    println!();

                    if buffer.starts_with(b"SQLite format 3") {
                        println!("✓ Extracted file is a standard SQLite database!");
                        println!("\nTry using: C:\\Codex\\Kalima\\datasets\\Noor dataset\\NoorQuranMorphologyV1.0.db");
                    } else {
                        println!("✗ Extracted file is also not standard SQLite");
                    }
                }
                Err(e) => println!("Cannot read extracted file: {}", e),
            }
        }
        Err(e) => println!("Extracted file not found ({})", e),
    }
}
