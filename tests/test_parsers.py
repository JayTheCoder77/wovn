from analysis.parsers.go import parse_go
from analysis.parsers.javascript import parse_javascript, parse_tsx, parse_typescript
from analysis.parsers.python import parse_python
from analysis.parsers.rust import parse_rust


def test_python_extracts_imports_and_entry():
    source = b'''
"""Demo module."""
import os
from pathlib import Path

class Greeter:
    """Says hi."""
    def hello(self, name: str) -> str:
        return name

def main() -> None:
    print(Greeter().hello("wovn"))

if __name__ == "__main__":
    main()
'''
    parsed = parse_python("app.py", source)
    names = {s.name for s in parsed.symbols}
    assert "Greeter" in names
    assert "hello" in names
    assert "main" in names
    assert parsed.is_entry_point
    assert any(item.module == "os" for item in parsed.imports)
    assert any("pathlib" in item.module for item in parsed.imports)


def test_typescript_exports_and_imports():
    source = b'''
import express from "express";
export function createApp() {
  const app = express();
  return app;
}
export class Router {}
'''
    parsed = parse_typescript("src/app.ts", source)
    assert any(item.module == "express" for item in parsed.imports)
    names = {s.name: s for s in parsed.symbols}
    assert names["createApp"].exported
    assert names["Router"].exported


def test_tsx_parses():
    source = b'''
export function Page() {
  return <div>Hi</div>;
}
'''
    parsed = parse_tsx("page.tsx", source)
    assert any(s.name == "Page" for s in parsed.symbols)


def test_javascript_parses():
    source = b'''
const { Command } = require("commander");
function cli() {}
module.exports = { cli };
'''
    parsed = parse_javascript("cli.js", source)
    assert parsed.language.value == "javascript"


def test_go_main_package():
    source = b'''
package main
import "flag"
func main() {
  flag.Parse()
}
func Helper() {}
'''
    parsed = parse_go("main.go", source)
    assert parsed.is_entry_point
    names = {s.name: s for s in parsed.symbols}
    assert names["Helper"].exported
    assert not names["main"].exported


def test_rust_pub_and_main():
    source = b'''
use clap::Parser;
pub fn run() {}
fn main() {}
pub struct Args {}
'''
    parsed = parse_rust("src/main.rs", source)
    assert parsed.is_entry_point
    names = {s.name: s for s in parsed.symbols}
    assert names["run"].exported
    assert names["Args"].exported
    assert not names["main"].exported
