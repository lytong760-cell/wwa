# wwa
## .ko language support

This repository now includes `ko.py`, a pragmatic interpreter for the .ko 1.3 syntax. It supports the required main block `[ ]`, typed declarations such as `int(100)*hp`, formatted output with `<printf>^(...)`, input assignment with `<input>(...)&=name`, global Random imports, function declarations/calls, class declarations with `!class` and `@private`, instance creation via `*Class*object`, method calls via `$object*method()`, `<now>` assignment, and multi-branch `<if>`/`<elif>`/`<else>` execution.

Run a .ko program with:

```bash
python ko.py examples/game.ko
```
