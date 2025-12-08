//! Configuration management for the Kalima API server.
//!
//! Loads configuration from environment variables with sensible defaults.
//! This eliminates hardcoded paths and makes the application more flexible
//! for different deployment scenarios.

use std::env;

#[derive(Debug, Clone)]
pub struct ServerConfig {
    /// Database file path or connection string
    pub database_path: String,

    /// Search index directory path
    pub index_path: String,

    /// Server bind address
    pub bind_address: String,

    /// Log level (trace, debug, info, warn, error)
    pub log_level: String,
}

impl ServerConfig {
    /// Load configuration from environment variables with fallback defaults.
    ///
    /// Environment variables:
    /// - `KALIMA_DB`: Database path (default: "data/database/kalima.db")
    /// - `KALIMA_INDEX`: Search index path (default: "data/search-index")
    /// - `KALIMA_BIND_ADDR`: Server bind address (default: "0.0.0.0:8080")
    /// - `RUST_LOG`: Log level (default: "info")
    pub fn from_env() -> Self {
        Self {
            database_path: env::var("KALIMA_DB")
                .unwrap_or_else(|_| "data/database/kalima.db".to_string()),
            index_path: env::var("KALIMA_INDEX")
                .unwrap_or_else(|_| "data/search-index".to_string()),
            bind_address: env::var("KALIMA_BIND_ADDR")
                .unwrap_or_else(|_| "0.0.0.0:8080".to_string()),
            log_level: env::var("RUST_LOG")
                .unwrap_or_else(|_| "info".to_string()),
        }
    }

    /// Create a configuration with explicit paths.
    ///
    /// Useful for testing or programmatic configuration.
    pub fn new(database_path: String, index_path: String) -> Self {
        Self {
            database_path,
            index_path,
            bind_address: "0.0.0.0:8080".to_string(),
            log_level: "info".to_string(),
        }
    }

    /// Validate configuration paths exist or can be created.
    ///
    /// Returns an error if paths are invalid or inaccessible.
    pub fn validate(&self) -> Result<(), String> {
        // Check if database directory exists
        if let Some(parent) = std::path::Path::new(&self.database_path).parent() {
            if !parent.exists() {
                return Err(format!(
                    "Database directory does not exist: {}",
                    parent.display()
                ));
            }
        }

        // Check if index directory exists or can be created
        let index_path = std::path::Path::new(&self.index_path);
        if let Some(parent) = index_path.parent() {
            if !parent.exists() {
                return Err(format!(
                    "Index directory parent does not exist: {}",
                    parent.display()
                ));
            }
        }

        Ok(())
    }
}

impl Default for ServerConfig {
    fn default() -> Self {
        Self::from_env()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_config() {
        let config = ServerConfig::default();
        assert!(!config.database_path.is_empty());
        assert!(!config.index_path.is_empty());
        assert_eq!(config.bind_address, "0.0.0.0:8080");
    }

    #[test]
    fn test_new_config() {
        let config = ServerConfig::new(
            "test.db".to_string(),
            "test-index".to_string(),
        );
        assert_eq!(config.database_path, "test.db");
        assert_eq!(config.index_path, "test-index");
    }
}
