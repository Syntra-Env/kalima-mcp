use kalima_index::TantivyIndex;
use kalima_core::{SegmentView, SearchBackend};
use tempfile::TempDir;
use std::sync::Arc;

#[tokio::test]
async fn test_index_creation_and_writing() -> anyhow::Result<()> {
    // Use a local directory to mimic user environment
    let path = std::path::PathBuf::from("kalima-index-test-local");
    if path.exists() {
        std::fs::remove_dir_all(&path)?;
    }
    
    println!("Creating index at {:?}", path);
    let index = TantivyIndex::open_or_create(&path)?;
    let index = Arc::new(index);

    // Create a dummy document
    let doc = SegmentView {
        id: "test-1".to_string(),
        verse_ref: "1:1".to_string(),
        token_index: 0,
        text: "test".to_string(),
        segments: vec![],
        annotations: vec![],
    };

    println!("Indexing document...");
    index.index_document(&doc).await?;
    index.commit()?;
    
    println!("Document indexed successfully.");
    
    // Try to open it again while the first one is alive (simulating potential concurrency or re-opening issues)
    println!("Attempting to open index again...");
    let index2 = TantivyIndex::open_or_create(&path);
    match index2 {
        Ok(_) => println!("Opened index again successfully."),
        Err(e) => println!("Failed to open index again: {:?}", e),
    }

    Ok(())
}

#[tokio::test]
async fn test_heavy_write_load() -> anyhow::Result<()> {
    let temp_dir = TempDir::new()?;
    let path = temp_dir.path().to_path_buf();
    
    let index = Arc::new(TantivyIndex::open_or_create(&path)?);

    for i in 0..100 {
        let doc = SegmentView {
            id: format!("test-{}", i),
            verse_ref: "1:1".to_string(),
            token_index: i,
            text: format!("text {}", i),
            segments: vec![],
            annotations: vec![],
        };
        if i % 10 == 0 {
            println!("Indexing batch {}", i);
        }
        index.index_document(&doc).await?;
    }
    index.commit()?;
    
    Ok(())
}
