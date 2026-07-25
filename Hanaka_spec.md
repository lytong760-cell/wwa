

---

## .ko 1.3 implementation note

The `.ko` runner lives in `ko.py`. It follows the 1.3 design where executable statements are collected from function bodies, class methods, or the mandatory anonymous main block `[ ]`. Top-level class and function definitions are registered before main execution so the sample game can instantiate `Hero`, call methods, read input, format output, and evaluate multi-branch status checks.
