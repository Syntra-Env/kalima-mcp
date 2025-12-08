use reqwest::blocking::Client;
use serde_json::Value;

fn client() -> Client {
    Client::builder()
        .timeout(std::time::Duration::from_secs(5))
        .build()
        .expect("client")
}

fn base_url() -> String {
    std::env::var("KALIMA_BASE_URL").unwrap_or_else(|_| "http://127.0.0.1:8080".to_string())
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
