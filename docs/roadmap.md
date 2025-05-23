
# 📍 NUGAMOTO – Development Roadmap

This file outlines the key development phases and goals for the Smart Kitchen Assistant project. It is intended to guide and track progress across both MVP implementation and future AI extensions.

---

## ✅ PHASE 1: Project Setup (DONE)
- [x] Define project name, scope, and branding (NUGAMOTO)
- [x] Design and document database schema
- [x] Create GitHub repository and commit project structure
- [x] Initialize `.env`, config, and requirements.txt
- [x] Establish FastAPI project layout with best practices

---

## 🚧 PHASE 2: Core API Development (IN PROGRESS)
### 🔹 User & Kitchen Module
- [ ] Create `User` CRUD endpoints
- [ ] Create `Kitchen` + `UserKitchen` linking
- [ ] Add health profile support

### 🔹 Inventory & Food Items
- [ ] CRUD endpoints for `InventoryItem`, `FoodItem`, `FoodItemAlias`
- [ ] Integrate minimum stock logic
- [ ] Manage `StorageLocation` setup

### 🔹 Recipes & Reviews
- [ ] CRUD for `Recipe`, `RecipeStep`, `RecipeIngredient`
- [ ] User `Review` creation and linking
- [ ] Add nutrition info via `RecipeNutrition`

### 🔹 Shopping Lists
- [ ] CRUD for `ShoppingList` and `ShoppingListItem`
- [ ] Auto-add items below min quantity

---

## 🧠 PHASE 3: AI Integration (SOON)
- [ ] Build AI service module (`services/ai_service.py`)
- [ ] Connect to OpenAI API for recipe generation
- [ ] Create `/recipes/generate/` endpoint
- [ ] Save prompts and results in `AIModelOutput`
- [ ] Enable prompt versioning and output logging

---

## 🔐 PHASE 4: Authentication (OPTIONAL / FUTURE)
- [ ] Add OAuth 2.0 + JWT support
- [ ] Protect endpoints and user-scoped queries
- [ ] Use `fastapi-users` or manual token handling

---

## 🔌 PHASE 5: External Data & Coaching (PLANNED)
- [ ] Link with OpenFoodFacts / USDA for nutrition
- [ ] Implement coaching interactions (habits, hydration, feedback)
- [ ] Begin vector DB and RAG exploration

---

## 📦 PHASE 6: Containerization & Deployment
- [ ] Prepare Dockerfile and `.dockerignore`
- [ ] Test local Docker build and run
- [ ] Deploy to platform (Render, Fly.io or similar)

---

## 📈 PHASE 7: UI/Frontend Integration
- [ ] Decide on frontend tech (React, Streamlit, etc.)
- [ ] Add API consumption from frontend
- [ ] Enable local tablet mode or dashboard

---

## 🧪 PHASE 8: Testing & QA
- [ ] Add Pytest with coverage for key modules
- [ ] Create `conftest.py` for fixtures
- [ ] Test AI responses and database correctness

---

## 🚀 PHASE 9: Finalization & Polish
- [ ] Clean up structure and unused files
- [ ] Update README.md and docs
- [ ] Record demo / screencast
- [ ] Write final project report

---

## 🗂 Tags
`#fastapi` `#ai` `#openai` `#sqlite` `#smartkitchen` `#python` `#nugamoto`
