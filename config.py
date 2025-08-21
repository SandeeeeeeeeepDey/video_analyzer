config={
# --- Sampling / randomness ---
"temperature": 1.0, # float [0.0–2.0]. Higher = more random/creative, lower = deterministic.
"top_p": 0.95, # float [0.0–1.0]. Nucleus sampling: only tokens with cumulative prob <= top_p.
"top_k": 64, # int. Top-k sampling: consider only top_k tokens by probability.


# --- Output length / repetition / candidates ---
"max_output_tokens": 8192, # int, maximum number of tokens generated (Gemini 2.5 Flash limit).
"candidate_count": 1, # int [1–8]. Number of candidate responses to return.


# --- Thinking (Gemini 2.5 only) ---
# "thinking_config": {
# "thinking_budget": -1 # int. -1 = dynamic (model decides), 0 = disable, >0 = reserve token budget.
# },


# --- Structured output / formatting ---
"response_mime_type": "text/plain", # "text/plain" = freeform text, "application/json" = structured JSON.
# "response_json_schema": <dict>, # JSON schema (only if response_mime_type="application/json").


# --- Decoding / generation penalties & control ---
# "stop_sequences": None, # list[str]. Model stops when sequence encountered.
# "seed": None, # int. Fix seed for deterministic outputs (when supported).
# "presence_penalty": 0.0, # float [-2.0–2.0]. Higher = discourage repeating existing existing tokens (encourage new topics).
# "frequency_penalty": 0.0, # float [-2.0–2.0]. Higher = discourage frequent repetition of same tokens.


# --- Safety / moderation ---
# "safety_settings": [...], # list[dict]. Configure safety filters (categories: harassment, hate, self-harm, sexual, etc.).


# --- Additional model-level fields ---
# "max_input_tokens": 32768, # int. Max number of tokens allowed in input prompt (Gemini 2.5 Flash).
}
