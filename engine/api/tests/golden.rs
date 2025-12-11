use common::{Annotation, SearchBackend, StorageBackend, Segment, SegmentView};
use search::TantivyIndex;
use store::{ConnectionRecord, SqliteStorage};

#[tokio::test]
async fn golden_search_annotation_connection() {
    let db_path = "sqlite::memory:";
    let tmp = tempfile::tempdir().unwrap();
    let index_path = tmp.path().join("index").to_string_lossy().to_string();
    let storage = SqliteStorage::connect(db_path).await.unwrap();
    let index = TantivyIndex::open_or_create(&index_path).unwrap();

    let doc = SegmentView {
        id: "1:1:0".into(),
        verse_ref: "1:1".into(),
        token_index: 0,
        text: "بسم".into(),
        segments: vec![Segment {
            id: "seg-1".into(),
            r#type: "stem".into(),
            form: "بسم".into(),
            root: Some("بسم".into()),
            lemma: Some("بسم".into()),
            pattern: Some("fa3l".into()),
            pos: Some("n".into()),
            verb_form: None,
            voice: None,
            mood: None,
            aspect: None,
            person: None,
            number: None,
            gender: None,
            case_: Some("gen".into()),
            dependency_rel: Some("nmod".into()),
        }],
        annotations: vec![],
    };

    storage.upsert_segment(&doc).await.unwrap();
    index.index_document(&doc).await.unwrap();
    index.commit().unwrap(); // Commit the index to make the document searchable

    // Search by root
    let hits = index
        .search_with_filters("", vec![("root".into(), vec!["بسم".into()])], 10)
        .await
        .unwrap();
    assert_eq!(hits.len(), 1);

    // Hydrate
    let hydrated = storage.hydrate_segments(&hits).await.unwrap();
    assert_eq!(hydrated[0].segments[0].root.as_deref(), Some("بسم"));

    // Annotation CRUD
    let ann = Annotation {
        id: "a1".into(),
        target_id: doc.id.clone(),
        layer: "note".into(),
        payload: serde_json::json!({"text":"hello"}),
    };
    storage.upsert_annotation(&ann).await.unwrap();
    let anns = storage.list_annotations(Some(&doc.id)).await.unwrap();
    assert_eq!(anns.len(), 1);
    storage.delete_annotation("a1").await.unwrap();

    // Connection CRUD
    let conn = ConnectionRecord {
        id: "c1".into(),
        from_token: doc.id.clone(),
        to_token: doc.id.clone(),
        layer: "internal".into(),
        meta: serde_json::json!({}),
    };
    storage.upsert_connection(&conn).await.unwrap();
    let conns = storage
        .list_connections_for_verse(1, 1)
        .await
        .unwrap();
    assert_eq!(conns.len(), 1);
    storage.delete_connection("c1").await.unwrap();
}
