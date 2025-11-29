#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .setup(|app| {
      if cfg!(debug_assertions) {
        app.handle().plugin(
          tauri_plugin_log::Builder::default()
            .level(log::LevelFilter::Info)
            .build(),
        )?;
      }

      configure_backend_paths();

      // Start the API server in background and wait for it to be ready
      tauri::async_runtime::spawn(async {
        kalima_api::start_server().await;
      });

      // Give the server time to bind to port 8080
      std::thread::sleep(std::time::Duration::from_millis(1000));

      Ok(())
    })
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}

fn configure_backend_paths() {
  use std::path::PathBuf;

  // Prefer paths next to the executable when packaged; fall back to cwd for dev.
  let exe_dir = std::env::current_exe()
    .ok()
    .and_then(|p| p.parent().map(|p| p.to_path_buf()))
    .unwrap_or_else(|| std::env::current_dir().unwrap_or_else(|_| PathBuf::from(".")));

  let resolve = |name: &str| -> PathBuf {
    let candidates = [
      exe_dir.join(name),
      exe_dir.join("resources").join(name),
      std::env::current_dir().unwrap_or_else(|_| PathBuf::from(".")).join(name),
      PathBuf::from(name),
    ];

    for path in candidates {
      if path.exists() {
        return path;
      }
    }

    exe_dir.join(name)
  };

  let db_path = resolve("kalima.db");
  let index_path = resolve("kalima-index");

  // Ensure index directory exists so Tantivy can open or create it.
  if !index_path.exists() {
    let _ = std::fs::create_dir_all(&index_path);
  }

  std::env::set_var("KALIMA_DB", db_path.to_string_lossy().to_string());
  std::env::set_var("KALIMA_INDEX", index_path.to_string_lossy().to_string());
}
