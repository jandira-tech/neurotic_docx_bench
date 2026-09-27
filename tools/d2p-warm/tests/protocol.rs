//! Exercise the worker's stdin/stdout contract with each feature-enabled converter.
//! Missing input files fail before any document parsing or font initialization.
use std::io::Write;
use std::process::{Command, Output, Stdio};

fn run(tool: Option<&str>, input: &str) -> Output {
    let mut command = Command::new(env!("CARGO_BIN_EXE_d2p-warm"));
    if let Some(tool) = tool {
        command.arg(tool);
    }
    let mut child = command
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("start warm worker");
    // Closing stdin is part of the protocol: the worker must finish on EOF.
    child.stdin.take().unwrap().write_all(input.as_bytes()).unwrap();
    child.wait_with_output().expect("collect worker output")
}

#[test]
fn missing_or_unknown_tool_exits_with_usage_without_protocol_output() {
    for tool in [None, Some("not-a-supported-converter")] {
        let output = run(tool, "");
        assert_eq!(output.status.code(), Some(2));
        assert!(output.stdout.is_empty());
        assert!(String::from_utf8(output.stderr).unwrap().contains("usage: d2p-warm"));
    }
}

#[cfg(any(feature = "jubarte", feature = "docxide", feature = "rdocx", feature = "office2pdf"))]
#[test]
fn malformed_requests_are_ignored_and_conversion_errors_do_not_stop_the_worker() {
    let tools = [
        #[cfg(feature = "jubarte")]
        "jubarte",
        #[cfg(feature = "docxide")]
        "docxide",
        #[cfg(feature = "rdocx")]
        "rdocx",
        #[cfg(feature = "office2pdf")]
        "office2pdf",
    ];
    // A fresh nonexistent parent prevents the test from reading or overwriting
    // user files. The carriage return also exercises single-line error framing.
    let parent = std::env::temp_dir().join(format!(
        "d2p-missing-{}-{}",
        std::process::id(),
        std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_nanos(),
    ));
    assert!(!parent.exists());
    let src = parent.join("missing\rsource.docx");
    let dst = parent.join("out.pdf");
    let input = format!("\nnot-a-request\n{}\t{}\n{}\t{}\n", src.display(), dst.display(), src.display(), dst.display());
    for tool in tools {
        let output = run(Some(tool), &input);
        assert!(output.status.success(), "{tool}: {:?}", output.stderr);
        let stdout = String::from_utf8(output.stdout).unwrap();
        assert!(!stdout.contains('\r'), "error messages must stay on one protocol line");
        let lines: Vec<_> = stdout.lines().collect();
        assert_eq!(lines.len(), 2, "{tool}: {stdout}");
        for line in lines {
            let fields: Vec<_> = line.splitn(3, ' ').collect();
            assert_eq!(fields.len(), 3, "{line}");
            assert_eq!(fields[0], "err");
            let elapsed: f64 = fields[1].parse().expect("numeric milliseconds");
            assert!(elapsed.is_finite() && elapsed >= 0.0);
            assert!(!fields[2].is_empty());
        }
        assert!(!dst.exists());
    }
}
