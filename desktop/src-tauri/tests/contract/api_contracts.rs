use reqwest::blocking::Client;
use serde_json::Value;
use std::path::PathBuf;
use std::sync::OnceLock;

fn client() -> Client {
    Client::builder()
        .timeout(std::time::Duration::from_secs(5))
        .build()
        .expect("client")
}

fn base_url() -> String {
    if let Ok(url) = std::env::var("KALIMA_BASE_URL") {
        return url;
    }

    static SERVER_URL: OnceLock<String> = OnceLock::new();
    SERVER_URL
        .get_or_init(|| start_test_api_server())
        .to_string()
}

fn start_test_api_server() -> String {
    fn find_repo_root() -> PathBuf {
        let tauri_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        tauri_dir
            .parent()
            .and_then(|p| p.parent())
            .map(|p| p.to_path_buf())
            .expect("repo root")
    }

    fn pick_port() -> u16 {
        std::net::TcpListener::bind(("127.0.0.1", 0))
            .expect("bind ephemeral port")
            .local_addr()
            .expect("local addr")
            .port()
    }

    let repo_root = find_repo_root();
    let db_path = repo_root.join("data").join("database").join("kalima.db");
    let index_path = repo_root.join("data").join("search-index");

    let port = pick_port();
    let url = format!("http://127.0.0.1:{port}");

    std::thread::spawn({
        let db_path = db_path.clone();
        let index_path = index_path.clone();
        move || {
            let runtime = tokio::runtime::Runtime::new().expect("tokio runtime");
            runtime.block_on(async move {
                let mut config = api::ServerConfig::new(
                    db_path.to_string_lossy().to_string(),
                    index_path.to_string_lossy().to_string(),
                );
                config.bind_address = format!("127.0.0.1:{port}");
                api::start_server_with_config(config).await;
            });
        }
    });

    // Wait for server to be ready.
    let health = format!("{url}/health");
    for _ in 0..60 {
        if let Ok(resp) = client().get(&health).send() {
            if resp.status().is_success() {
                return url;
            }
        }
        std::thread::sleep(std::time::Duration::from_millis(100));
    }

    panic!("API server did not start: {health}");
}

#[test]
fn verse_shape_matches_contract() {
    let url = format!("{}/api/verse/1/1", base_url());
    let v: Value = client()
        .get(url)
        .send()
        .unwrap()
        .error_for_status()
        .unwrap()
        .json()
        .unwrap();

    assert!(v.get("surah").is_some(), "missing surah");
    assert_eq!(v.get("ayah").and_then(Value::as_i64), Some(1));
    assert!(
        v.get("text").and_then(Value::as_str).is_some(),
        "missing text"
    );
    if let Some(tokens) = v.get("tokens").and_then(Value::as_array) {
        for t in tokens {
            assert!(t.get("segments").is_some(), "token missing segments");
        }
    }
}

#[test]
fn morphology_shape_matches_contract() {
    let url = format!("{}/api/morphology/1/1", base_url());
    let v: Value = client()
        .get(url)
        .send()
        .unwrap()
        .error_for_status()
        .unwrap()
        .json()
        .unwrap();
    assert_eq!(v.get("surah").and_then(Value::as_i64), Some(1));
    assert_eq!(v.get("ayah").and_then(Value::as_i64), Some(1));
    if let Some(morph) = v.get("morphology").and_then(Value::as_array) {
        for seg in morph {
            assert!(seg.get("text").is_some(), "segment missing text");
        }
    }
}

#[test]
fn dependency_shape_matches_contract() {
    let url = format!("{}/api/dependency/1/1", base_url());
    let v: Value = client()
        .get(url)
        .send()
        .unwrap()
        .error_for_status()
        .unwrap()
        .json()
        .unwrap();
    assert_eq!(v.get("surah").and_then(Value::as_i64), Some(1));
    assert_eq!(v.get("ayah").and_then(Value::as_i64), Some(1));
    if let Some(deps) = v.get("dependency_tree").and_then(Value::as_array) {
        for d in deps {
            assert!(d.get("rel_label").is_some(), "dependency missing rel_label");
            assert!(d.get("word").is_some(), "dependency missing word");
        }
    }
}
