---
name: calculator-usage
description: How to use the acme-mcp maths tools. Use whenever arithmetic is needed — choose the matching operation, pass two numbers, and present the returned result without recomputing it mentally.
tags: ["maths"]
---

# Using the acme-mcp maths tools

Use the tool that names the operation the user requested:

- `addition(a, b)` adds two numbers.
- `subtraction(a, b)` subtracts `b` from `a`.
- `multiplication(a, b)` multiplies two numbers.
- `division(a, b)` divides `a` by `b` and rejects a zero divisor.

For a calculation with several steps, call one tool per step and feed the
returned value into the next call. Preserve the operation order the user gave;
do not silently rewrite it. Present the final tool result directly and retain
its decimal part when division returns a float.
