# MCP integration points for AI reuse

## Prompt construction dependencies
- `PromptSectionBuilder` requires a SQLAlchemy `Session` so it can build helper services (`UnitConversionService` and `InventoryPromptService`) before rendering templates. These helpers format inventory quantities and prioritize ingredients, so any MCP tool that calls into section builders must either provide a live session or mock the conversion and inventory utilities.【F:backend/services/ai/prompt_builder.py†L25-L109】
- `PromptBuilder` composes the section builder with high-level orchestration methods. Both `build_recipe_prompt` and `build_inventory_analysis_prompt` hydrate a `PromptContext` via `PromptContext.build_from_ids`, which queries users, inventory, and kitchen equipment. MCP wrappers should therefore accept `user_id`, `kitchen_id`, and a `RecipeGenerationRequest` so they can reuse the existing context-building flow rather than reimplementing data loaders.【F:backend/services/ai/prompt_builder.py†L192-L326】【F:backend/schemas/ai_service.py†L25-L96】
- The prompt builder expects a `RecipeGenerationRequest` schema instance. The schema captures cuisine preferences, time limits, dietary restrictions, appliance requirements, and toggles for prioritizing expiring or available items. MCP tools should surface these fields directly so requests stay compatible with downstream validation.【F:backend/schemas/ai_service.py†L138-L200】

## AI service instantiation
- `AIServiceFactory.create_ai_service` maps provider names (currently only `"openai"`) to concrete implementations. The factory defaults to `settings.DEFAULT_AI_PROVIDER` (falling back to OpenAI) so MCP entry points can rely on a single factory call and honor environment overrides.【F:backend/services/ai/factory.py†L12-L50】
- `OpenAIService` depends on a SQLAlchemy session, an OpenAI model name (default `gpt-4o-mini`), and an API key. The key is read from `settings.OPENAI_API_KEY`, so deployments must expose that environment variable (or override it when constructing the service). If no key is available the service raises `OpenAIServiceError` during initialization.【F:backend/services/ai/openai_service.py†L36-L60】

## Runtime interactions worth exposing via MCP
- Wrap `PromptBuilder.build_recipe_prompt` and `PromptBuilder.build_inventory_analysis_prompt` so MCP tools can return the generated system/user prompt pair for inspection, debugging, or prompt-tuning workflows without needing to call the language model.【F:backend/services/ai/prompt_builder.py†L198-L326】
- Wrap the `OpenAIService` coroutine entry points—`generate_recipe`, `analyze_inventory`, and `get_cooking_suggestions`—to give MCP clients a uniform way to trigger AI calls. Each method already packages prompts and handles structured/JSON responses, so exposing them avoids duplicating OpenAI client logic.【F:backend/services/ai/openai_service.py†L62-L211】
- For lower-level experimentation, optional MCP tools could surface `_create_structured_completion` and `_create_json_completion`. These helpers accept raw prompt strings plus token/temperature overrides, providing a test bed for new schemas or response formats while still enforcing OpenAI error handling.【F:backend/services/ai/openai_service.py†L213-L334】

## Configuration checklist for MCP deployments
- Ensure `OPENAI_API_KEY` is present in the environment (or injected when constructing `OpenAIService`) so the factory-created service initializes successfully.【F:backend/services/ai/openai_service.py†L52-L59】
- Optionally set `DEFAULT_AI_PROVIDER` in configuration to switch the factory’s default provider without code changes. In the absence of this setting the system assumes OpenAI, so MCP tools can document OpenAI as the baseline provider unless overridden.【F:backend/services/ai/factory.py†L39-L50】
