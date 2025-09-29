# MCP Domain Map

This document maps the FastAPI v1 routers to prospective MCP tool intents. It captures the base tags/summaries exposed from `backend/main.py`, the key endpoints grouped by intent, and highlights authentication or kitchen scoping requirements alongside the primary request/response schemas.

## Router overview for `/v1`

| Router module | Base path under `/v1` | Declared tags | High-level summary |
| --- | --- | --- | --- |
| `backend.api.v1.auth` | `/auth` | `Auth` | User registration, login, token refresh, and logout flows. |
| `backend.api.v1.user_me` | `/users` | `Users` | Current-user self profile retrieval. |
| `backend.api.v1.core` | `/units`, `/units/conversions` | `Unit Management`, `Unit Conversion` | Shared unit catalog and conversion utilities. |
| `backend.api.v1.device` | `/devices/...` | `Device Types`, `Appliances`, `Kitchen Tools`, `Device Summary` | Device catalog plus kitchen-scoped appliance/tool management. |
| `backend.api.v1.food` | `/food-items/...` | `Food Items`, `Food Item Aliases`, `Food Item Conversions`, `Food Item Operations` | Food dictionary with aliases, conversions, and conversion utilities. |
| `backend.api.v1.inventory` | `/storage-locations`, `/items` | `Storage Locations`, `Inventory Items` | Kitchen inventory storage locations and stock tracking. |
| `backend.api.v1.kitchen` | `/kitchens/...` | `Kitchens`, `Kitchen Users` | Kitchen lifecycle and membership management. |
| `backend.api.v1.recipe` | `/recipes/...` | `Recipes`, `Recipe Ingredients`, `Recipe Steps`, `Recipe Nutrition`, `Recipe Reviews` | Recipe authoring, detailed editing, reviews, and cooking operations. |
| `backend.api.v1.shopping` | `/shopping...` | `Shopping Lists`, `Shopping List Product Assignments`, `Shopping Products` | Global shopping product catalog and kitchen shopping lists. |
| `backend.api.v1.user` | `/users` | `Users` | Administrative user CRUD plus self-service updates. |
| `backend.api.v1.user_credentials` | `/users` | `User Credentials` | Self-managed credential profile CRUD. |
| `backend.api.v1.user_health` | `/users` | `User Health Profiles` | Self-managed health profile CRUD and search. |
| `backend.api.v1.ai_model_output` | `/ai` | `AI Outputs` | Stored AI outputs with admin summaries. |
| `backend.api.v1.ai_service_recipe` | `/ai` | `AI Services` | AI-powered recipe generation, conversion, and status updates. |

---

## Authentication & Session Management (Auth)

- **POST `/v1/auth/register`** — Register a new account and issue access/refresh tokens.
  - Dependencies: `Depends(get_db)`.
  - Payloads: `RegisterRequest` body; creates `UserCreate` and `UserCredentialsCreate` internally; responds with `TokenPair`.
  - Notes: Auto-applies admin claims if email/domain is whitelisted.
- **POST `/v1/auth/login`** — Authenticate with email/password for JWTs.
  - Dependencies: `Depends(get_db)`.
  - Payloads: `LoginRequest` body; returns `TokenPair`.
- **POST `/v1/auth/refresh`** — Refresh access token using a refresh token.
  - Dependencies: `Depends(get_db)`.
  - Payloads: raw `refresh_token` string body; responds with `TokenPair`.
- **POST `/v1/auth/logout`** — Stateless logout helper.
  - Dependencies: none (client deletes tokens).

## User Self Profile Intent

- **GET `/v1/users/me`** — Retrieve current authenticated user profile.
  - Dependencies: `Depends(get_current_user)` yields `UserRead`.

## Core Units & Conversions Intent

_All unit endpoints require authentication; mutation operations further require super-admin rights._

### Unit catalog (`/v1/units` — tag `Unit Management`)

- **POST `/v1/units/`** — Create unit.
  - Dependencies: `Depends(get_current_user_id)`, `Depends(get_db)`.
  - Payload: `UnitCreate`; responds with `UnitRead`.
- **GET `/v1/units/`** — List units with optional `UnitType` filter.
  - Dependencies: `Depends(get_current_user_id)`, `Depends(get_db)`.
- **GET `/v1/units/{unit_id}`** — Fetch unit by id.
  - Dependencies: `Depends(get_current_user_id)`, `Depends(get_db)`.
- **PATCH `/v1/units/{unit_id}`** — Update unit (admin only).
  - Dependencies: `Depends(require_super_admin)`, `Depends(get_db)`.
  - Payload: `UnitUpdate` → `UnitRead`.
- **DELETE `/v1/units/{unit_id}`** — Delete unit (admin only, safeguards conversions).
  - Dependencies: `Depends(require_super_admin)`, `Depends(get_db)`.
- **GET `/v1/units/{unit_id}/conversions`** — Unit with attached conversions.
  - Dependencies: `Depends(get_current_user_id)`, `Depends(get_db)`; responds with `UnitWithConversions`.

### Unit conversions (`/v1/units/conversions` — tag `Unit Conversion`)

- **POST `/v1/units/conversions/`** — Create conversion between units.
  - Dependencies: `Depends(get_current_user_id)`, `Depends(get_db)`.
  - Payload: `UnitConversionCreate` → `UnitConversionRead`.
- **GET `/v1/units/conversions/`** — Query conversions (by from/to unit).
  - Dependencies: `Depends(get_current_user_id)`, `Depends(get_db)`.
- **PATCH `/v1/units/conversions/{from_unit_id}/{to_unit_id}`** — Update factor (admin).
  - Dependencies: `Depends(require_super_admin)`, `Depends(get_db)`.
  - Payload: `UnitConversionUpdate`.
- **DELETE `/v1/units/conversions/{from_unit_id}/{to_unit_id}`** — Remove conversion (admin).
  - Dependencies: `Depends(require_super_admin)`, `Depends(get_db)`.
- **POST `/v1/units/{from_unit_id}/convert-to/{to_unit_id}`** — Convert value between units.
  - Dependencies: `Depends(get_current_user_id)`, `Depends(get_db)`.
  - Payload: query `value` parameter; responds with `ConversionResult`.
- **GET `/v1/units/{from_unit_id}/can-convert-to/{to_unit_id}`** — Check convertibility.
  - Dependencies: `Depends(get_current_user_id)`, `Depends(get_db)`.

## Device Catalog & Kitchen Device Intent

### Global device types (`/v1/devices/device-types` — tag `Device Types`)

- CRUD endpoints for `DeviceTypeCreate`, `DeviceTypeUpdate`, `DeviceTypeRead` with auth required for create/read and `require_super_admin` for update/delete.

### Kitchen appliances (`/v1/devices/kitchens/{kitchen_id}/appliances` — tag `Appliances`)

- Create/update/delete appliances with `require_kitchen_role({KitchenRole.OWNER, KitchenRole.ADMIN})`.
- Read/search/list appliances with `require_kitchen_member()`.
- Payload schemas: `ApplianceCreate`, `ApplianceUpdate`, `ApplianceSearchParams`, responses include `ApplianceRead` or `ApplianceWithDeviceType`.

### Kitchen tools (`/v1/devices/kitchens/{kitchen_id}/tools` — tag `Kitchen Tools`)

- Same auth split as appliances using `KitchenRole` checks.
- Payloads: `KitchenToolCreate`, `KitchenToolUpdate`, `KitchenToolSearchParams`, returning `KitchenToolRead` / `KitchenToolWithDeviceType`.

### Device summary (`/v1/devices/kitchens/{kitchen_id}/devices/summary` — tag `Device Summary`)

- Requires `require_kitchen_member()`; responds with `KitchenDeviceSummary`.

## Food Dictionary & Conversion Intent

### Food items (`/v1/food-items` — tag `Food Items`)

- Create/list/get food items requires `get_current_user_id`; updates/deletes gated by `require_super_admin`.
- Payloads: `FoodItemCreate`, `FoodItemUpdate`, responses `FoodItemRead`, `FoodItemWithConversions`, `FoodItemWithAliases`.

### Food aliases (`/v1/food-items/aliases/...` — tag `Food Item Aliases`)

- Create/list operations require `get_current_user_id`; delete uses `require_super_admin`.
- Payloads: `FoodItemAliasCreate`, `FoodItemAliasRead`.

### Food-specific unit conversions (`/v1/food-items/conversions/...` — tag `Food Item Conversions`)

- Create/list require `get_current_user_id`; delete uses `require_super_admin`.
- Payloads: `FoodItemUnitConversionCreate`, `FoodItemUnitConversionRead`.

### Food operations (`/v1/food-items/operations/...` — tag `Food Item Operations`)

- Alias search and conversion utilities require `get_current_user_id`.
- Payload: conversion uses query parameters plus `FoodConversionResult` response.

## Kitchen Inventory Intent

### Storage locations (`/v1/storage-locations` — tag `Storage Locations`)

- Owner/admin can create/update/delete via `require_kitchen_role({KitchenRole.OWNER, KitchenRole.ADMIN})`.
- Members (`require_kitchen_member()`) can list/get.
- Payloads: `StorageLocationCreate`, `StorageLocationUpdate`, responses `StorageLocationRead`.

### Inventory items (`/v1/items` — tag `Inventory Items`)

- Owner/admin create/update/delete using `InventoryItemCreate`/`InventoryItemUpdate`.
- Members can list items and access analysis endpoints (low-stock/expiring/expired).

## Kitchen Collaboration Intent

### Kitchens (`/v1/kitchens` — tag `Kitchens`)

- **POST `/v1/kitchens/`** — Create kitchen. Requires `Depends(get_current_user_id)`; payload `KitchenCreate`; response `KitchenRead`.
- **GET `/v1/kitchens/`** — List kitchens for current user. Requires `get_current_user_id`.
- **GET `/v1/kitchens/{kitchen_id}`** — Kitchen with members; requires `require_kitchen_member()`; returns `KitchenWithUsers`.
- **PATCH `/v1/kitchens/{kitchen_id}`**, **DELETE `/v1/kitchens/{kitchen_id}`** — Require `require_kitchen_role({KitchenRole.OWNER, KitchenRole.ADMIN})`; payload `KitchenUpdate` for patch.

### Kitchen membership (`/v1/kitchens/users/...` — tag `Kitchen Users`)

- Add/update/remove members require owner/admin role; payloads `UserKitchenCreate`, `UserKitchenUpdate`.
- Fetch role (`GET /{kitchen_id}/{user_id}`) needs `require_kitchen_member()`.
- `GET /{user_id}/kitchens` uses `get_current_user_id` to ensure self-only listing.

## Recipe Authoring & Execution Intent

### Recipes (`/v1/recipes` — tag `Recipes`)

- Create/list/summary/suggestions/AI-generated fetch require `get_current_user_id`.
- `RecipeCreate`, `RecipeSearchParams`, `RecipeSummary`, `RecipeRead`, `RecipeWithDetails` used in payloads/responses.
- Update/delete guarded by `require_recipe_owner_or_admin` with `RecipeUpdate`.
- `POST /{recipe_id}/cook` requires kitchen membership via `require_kitchen_member()` and a `kitchen_id` query; responds with `RecipeCookResponse` or errors using `InsufficientIngredientsError`.

### Ingredients (`/v1/recipes/{recipe_id}/ingredients` — tag `Recipe Ingredients`)

- Owner/admin can add/update/delete using `RecipeIngredientCreate`/`RecipeIngredientUpdate`.
- Authenticated users can list via `get_current_user_id`.

### Steps (`/v1/recipes/{recipe_id}/steps` — tag `Recipe Steps`)

- Owner/admin can add/update/delete using `RecipeStepCreate`/`RecipeStepUpdate`.
- Authenticated users can list.

### Nutrition (`/v1/recipes/{recipe_id}/nutrition` — tag `Recipe Nutrition`)

- Owner/admin can create/update/delete nutrition via `RecipeNutritionCreate`/`RecipeNutritionUpdate`.

### Reviews (`/v1/recipes/{recipe_id}/reviews` — tag `Recipe Reviews`)

- Self-serve review CRUD uses `require_same_user` with `RecipeReviewUpsert` and `RecipeReviewUpdate` payloads.
- Authenticated users can list reviews and rating summaries.

## Shopping Planning Intent

### Global products (`/v1/shopping/shopping-products` — tag `Shopping Products`)

- Authenticated users can create/search/get (`ShoppingProductCreate`, `ShoppingProductSearchParams`).
- Admin-only update/delete with `require_super_admin` and `ShoppingProductUpdate`.
- Additional helper: `GET /by-food-item/{food_item_id}` for authenticated users.

### Kitchen shopping lists (`/v1/shopping/kitchens/{kitchen_id}/shopping-lists` — tag `Shopping Lists`)

- Owner/admin create/update/delete using `ShoppingListCreate`, `ShoppingListUpdate`.
- Members list/get view and fetch with products (`ShoppingListWithProducts`).

### Product assignments (`/v1/shopping/kitchens/{kitchen_id}/shopping-lists/{list_id}/products` — tag `Shopping List Product Assignments`)

- Owner/admin assign products (`ShoppingProductAssignmentCreate`) or combined create-and-assign (`ShoppingProductCreateWithAssignment`).
- Members list assignments using search filters (`ShoppingProductAssignmentSearchParams`).
- Owner/admin update/delete assignments via `ShoppingProductAssignmentUpdate` or removal endpoint.

## User Administration & Profiles Intent

### Users (`/v1/users` — tag `Users`)

- Admin-only user creation via `require_super_admin` with `UserCreate`.
- Authenticated listing via `get_current_user_id`.
- Self-only get/update/delete using `require_same_user` and `UserUpdate`.
- `GET /by-email/{email}` requires auth and enforces self-check against `get_current_user_id`.

### User credentials (`/v1/users/{user_id}/credentials` — tag `User Credentials`)

- Self-only create/get/update using `require_same_user`; payloads `UserCredentialsCreate`, `UserCredentialsUpdate`; returns `UserCredentialsRead`.
- `GET /credentials/summary` accessible to any authenticated user (`get_current_user_id`) returning `UserCredentialsSummary` list.

### User health profiles (`/v1/users/{user_id}/health-profile` — tag `User Health Profiles`)

- Self-only create/get/update using `require_same_user`; payloads `UserHealthProfileCreate`, `UserHealthProfileUpdate`; returns `UserHealthProfileRead`.
- `GET /health-profiles/summary` and `/health-profiles/search` available to authenticated users via `get_current_user_id`, returning `UserHealthProfileSummary` lists.

## AI Output History Intent

- **POST `/v1/ai/outputs/`** — Store AI output (`AIModelOutputCreate`) requiring self-only enforcement through `get_current_user_id`.
- **GET `/v1/ai/outputs/{output_id}`** — Owner-only unless `_is_admin` (checks JWT claims). Requires `get_current_user_id` and optional HTTP bearer token for admin detection.
- **DELETE `/v1/ai/outputs/{output_id}`**, **GET `/v1/ai/outputs/summary`** — Admin only via `require_super_admin`.
- **GET `/v1/ai/outputs/`** and **`/targets/{target_type}/{target_id}`** — Authenticated; non-admins implicitly filtered to their own user id.
- Payload schemas include `AIModelOutputRead`, `AIOutputSearchParams`, `AIOutputSummary`.

## AI Recipe Services Intent

- **POST `/v1/ai/recipes`** — Generate recipe via AI.
  - Dependencies: `Depends(get_db)`, `Depends(get_current_user_id)` plus manual kitchen membership check via `crud_kitchen.get_user_kitchen_relationship`.
  - Payloads: `RecipeGenerationAPIRequest`; returns `RecipeWithAIOutput` (contains `RecipeGenerationResponse` and persisted `AIModelOutputCreate`).
- **POST `/v1/ai/recipes/{ai_output_id}/convert-to-recipe-create`** — Convert stored AI response into `RecipeCreate` (self-only via `require_same_user`).
- **PATCH `/v1/ai/recipes/{ai_output_id}/mark-saved`** — Mark AI output saved (self-only) using `AIModelOutputUpdate` with recipe binding.

---

### Notes on scopes & dependencies

- `require_super_admin` restricts administrative operations (unit, device type, shopping product maintenance, AI summaries).
- `require_kitchen_member()` and `require_kitchen_role(...)` enforce kitchen-level authorization for inventory, device, shopping, and cooking flows.
- `require_recipe_owner_or_admin` and `require_same_user` protect recipe editing, reviews, and user/AI artifacts.
- Database access is consistently mediated via `Depends(get_db)` across routers, ensuring transactional consistency for MCP tool calls.

