# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Learners, project reviewers, and operational analysts exploring real Olist order, payment, delivery, and customer-review data through natural-language questions.

## Product Purpose

The Logistics & Order Intelligence Chatbot turns plain-English questions into safe, read-only analysis of the Olist Brazilian e-commerce dataset and returns an understandable answer.

## Positioning

It combines a provider-selectable LLM with explicit SQL validation, categorical-value checking, read-only execution, and a bounded repair loop instead of using an autonomous SQL agent.

## Operating Context

Users select an LLM provider, ask logistics or sales questions, review the plain-English answer, and may inspect the route and generated SQL.

## Capabilities and Constraints

- Olist is a real, anonymized Brazilian marketplace dataset with approximately 100,000 orders from 2016–2018.
- Queries are restricted to `SELECT` statements and allow-listed tables, and database access is read-only.
- The app can also search customer-review text for sentiment questions.
- The provider is chosen at runtime from Groq, Gemini, or local Ollama.
- The web experience is an interface for the existing API; it must not imply live, real-time, or cross-border export data.

## Brand Commitments

The user has requested a dark, animated experience built around an interactive cursor-following robot, with a landing-to-chat transition and an expressive AI assistant interface.

## Evidence on Hand

- Project truth and safety constraints: `PROJECT.md` and `README.md`.
- Web interface: `web/src/app/page.tsx`.
- Robot scene: user-provided Spline scene URL.

## Product Principles

1. Make the safety boundary visible without making the workflow feel restrictive.
2. Keep data questions quick to ask and answers easy to scan.
3. Use animation to explain state changes, not delay analysis.
4. Preserve honest claims about the Olist dataset and its limits.
