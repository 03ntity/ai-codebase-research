struct App {
    name: String,
}

fn main() {
    let app = App {
        name: "demo".to_string(),
    };
    println!("{}", app.name);
}
