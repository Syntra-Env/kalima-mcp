#[tokio::main]
async fn main() {
    kalima_api::start_server().await;
}
