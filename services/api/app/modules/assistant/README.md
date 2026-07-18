# Module: assistant

The assistant implements a provider-independent model adapter and a tool-calling
loop. Models can call only whitelisted application tools and cannot access Cloud
SQL or BigQuery directly. A hosted provider is used first; `services/llm` is a
deferred self-hosting option.
