# FMMS Backend (Factory Material Management System)

Backend API built with **FastAPI** + **SQLAlchemy**, currently using **SQLite**
(temporary, for development). Switching to PostgreSQL later only requires
changing one line in `app/database/connection.py` -- no model code changes.

## Setup (run these on your local machine, not in a sandbox)

```bash
# 1. Create a virtual environment
python -m venv venv

# 2. Activate it
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the server
uvicorn main:app --reload
```

Once running, open:
- **http://127.0.0.1:8000/docs** -> interactive Swagger UI to test every API directly in the browser
- **http://127.0.0.1:8000/** -> basic health check

A file named `fmms.db` will be created automatically in this folder the first
time you run the server -- that is your SQLite database. You can open it with
a free tool like "DB Browser for SQLite" to see the actual tables/data.

## Automated Test Script (test_api.py)

Instead of testing each endpoint manually in Swagger UI, you can run a single
script that calls every endpoint in sequence and reports PASS/FAIL for each.

**How to use:**
1. In one terminal, start the server: `uvicorn main:app --reload`
2. In a **second terminal** (same venv activated), run:
   ```bash
   python test_api.py
   ```

The script logs in using an existing user (edit the `EXISTING_USER_EMAIL` /
`EXISTING_USER_PASSWORD` constants at the top of `test_api.py` if your
credentials differ), then walks through: Roles -> Login -> Items ->
Warehouses -> Suppliers -> Customers -> Purchase Orders.

Each run creates fresh test records (item codes, PO numbers, etc. include a
unique timestamp suffix) so you can re-run it repeatedly without "already
exists" errors. At the end it prints a summary of how many steps passed/failed.

If a step fails, the script prints the exact response body so you can see
what went wrong without digging through server logs.

## Project Structure

```
fmms_backend/
├── main.py                  # App entry point - run this file
├── requirements.txt         # Python dependencies
├── app/
│   ├── database/
│   │   └── connection.py    # DB connection setup (SQLite for now)
│   ├── models/               # SQLAlchemy models (= database tables)
│   │   ├── user.py           # Role, User, UserLocation
│   │   ├── warehouse.py      # Warehouse
│   │   ├── item.py           # Item (Item Master)
│   │   └── partners.py       # Supplier, Customer
│   ├── schemas/               # Pydantic schemas (API request/response shapes)
│   │   └── item.py
│   └── routers/                # API endpoints, grouped by feature
│       └── items.py            # Item Master CRUD APIs
```

## What's working right now

### Module: Authentication
| Method | Endpoint        | Description                                  | Auth required? |
|--------|------------------|-----------------------------------------------|-----------------|
| GET    | /roles/          | List all available roles (id + name) -- use this to know which `role_id` to pass when registering | No |
| POST   | /auth/register   | Create a new user                             | No (open for now) |
| POST   | /auth/login      | Login with email (as "username") + password (form-data, not JSON), returns JWT token | No |
| GET    | /auth/me         | Get currently logged-in user's details        | Yes            |

Default roles are auto-created on first run: `Admin`, `Store Manager`, `Production Manager`, `Operator`, `Accountant`.
Call `GET /roles/` (no login needed) to see the exact id for each role name -- don't assume or hardcode the ids, always check via this endpoint since the order they were seeded in determines their id.

### Module 1: Master Data - Item Categories (no auth required)
| Method | Endpoint              | Description                              |
|--------|------------------------|--------------------------------------------|
| GET    | /item-categories/      | List valid item categories (value + label), for use as a dropdown when creating/editing an item |

Unlike Roles, these are NOT stored in the database -- they are a small fixed
list defined in `app/constants.py` (`ITEM_CATEGORIES`). This is intentional:
categories like "Raw Material" / "Semi-Finished" / "Finished Good" are part
of the application's core logic, not data a user manages day-to-day. If you
ever need to add a new category, update both `ITEM_CATEGORIES` in
`app/constants.py` and the `ItemCategory` Literal type in `app/schemas/item.py`.

### Module 1: Master Data - Items (now protected, requires login)
| Method | Endpoint          | Description                          |
|--------|--------------------|---------------------------------------|
| POST   | /items/            | Create a new item                     |
| GET    | /items/            | List all items (supports ?search= and ?category=) |
| GET    | /items/{id}        | Get a single item                     |
| PUT    | /items/{id}        | Update an item                        |
| DELETE | /items/{id}        | Delete an item                        |

### Module 1: Master Data - Warehouses (protected)
| Method | Endpoint              | Description                              |
|--------|------------------------|--------------------------------------------|
| POST   | /warehouses/           | Create a new warehouse/plant/godown         |
| GET    | /warehouses/           | List all warehouses                         |
| GET    | /warehouses/{id}       | Get a single warehouse                      |
| PUT    | /warehouses/{id}       | Update a warehouse                          |
| DELETE | /warehouses/{id}       | Deactivate a warehouse (soft delete -- sets is_active=False, does not remove the row, since other tables reference it) |

### Module 1: Master Data - Suppliers (protected)
| Method | Endpoint              | Description                              |
|--------|------------------------|--------------------------------------------|
| POST   | /suppliers/            | Create a new supplier                       |
| GET    | /suppliers/            | List all suppliers (supports ?search=)      |
| GET    | /suppliers/{id}        | Get a single supplier                       |
| PUT    | /suppliers/{id}        | Update a supplier                           |
| DELETE | /suppliers/{id}        | Delete a supplier                           |

### Module 1: Master Data - Customers (protected)
| Method | Endpoint              | Description                              |
|--------|------------------------|--------------------------------------------|
| POST   | /customers/            | Create a new customer                       |
| GET    | /customers/            | List all customers (supports ?search=)      |
| GET    | /customers/{id}        | Get a single customer                       |
| PUT    | /customers/{id}        | Update a customer                           |
| DELETE | /customers/{id}        | Delete a customer                           |

### Module 2: Purchase Orders (protected)
| Method | Endpoint                          | Description                              |
|--------|-------------------------------------|--------------------------------------------|
| POST   | /purchase-orders/                  | Create a new PO with its line items (single request) |
| GET    | /purchase-orders/                  | List all POs (supports ?status= and ?supplier_id=) |
| GET    | /purchase-orders/{id}              | Get one PO with full item details           |
| PATCH  | /purchase-orders/{id}/status       | Update PO status: pending / partial / completed / cancelled |
| DELETE | /purchase-orders/{id}              | Cancel a PO (sets status to "cancelled", does not delete the row) |

**Important:** Creating a PO does NOT affect stock. A PO just records "we ordered
this material." Stock only changes once a GRN (Goods Receipt Note) is created
against this PO when the material physically arrives -- see the GRN module below.

> **Bug fix note (stock_helper.py):** `record_stock_movement()` now flushes
> the session immediately after adding each ledger entry. Without this, calling
> the function multiple times for the SAME item+warehouse within one request
> (e.g. a production order issuing a raw material and then recording wastage
> for that same item) would calculate the running balance from a stale value,
> since the database query inside `get_current_stock()` couldn't see the
> not-yet-flushed entry from the previous call. Fixed by flushing after every
> stock movement, so each subsequent call in the same transaction sees the
> correct up-to-date balance.

**Example request body for `POST /purchase-orders/`:**
```json
{
  "po_number": "PO-2026-001",
  "supplier_id": 1,
  "warehouse_id": 1,
  "items": [
    { "item_id": 1, "ordered_qty": 500, "rate": 45.50 },
    { "item_id": 2, "ordered_qty": 200, "rate": 120.00 }
  ]
}
```
You'll need an existing supplier (`/suppliers/`), warehouse (`/warehouses/`),
and item(s) (`/items/`) created first -- use their returned `id` values here.

### Module 2: GRN - Goods Receipt Note (protected)

This is where stock actually gets updated. A GRN records material that has
physically arrived against a specific PO, including a quality check
(accepted vs rejected quantity per line item). Only **accepted_qty** is
added to stock -- rejected material is recorded for traceability but never
enters the stock ledger.

| Method | Endpoint        | Description                              |
|--------|------------------|--------------------------------------------|
| POST   | /grn/            | Create a GRN against a PO (updates stock automatically) |
| GET    | /grn/            | List all GRNs (supports ?po_id=)            |
| GET    | /grn/{id}        | Get one GRN with full item details          |

**What happens automatically when you create a GRN:**
1. Validates the PO exists, and is not `cancelled` or already `completed`.
2. Validates every item in the GRN actually belongs to that PO.
3. For each line item, `accepted_qty + rejected_qty` must equal `received_qty` (validated automatically -- you'll get a clear error if they don't add up).
4. Records a stock movement (`GRN_IN`) for the accepted quantity only.
5. Re-checks the PO: if every line item's total accepted quantity (across all GRNs so far) meets or exceeds what was ordered, the PO becomes `completed`; otherwise `partial`.

**Example request body for `POST /grn/`:**
```json
{
  "grn_number": "GRN-2026-001",
  "po_id": 1,
  "received_date": "2026-06-22",
  "items": [
    { "item_id": 1, "received_qty": 300, "accepted_qty": 295, "rejected_qty": 5, "batch_number": "BATCH-001" },
    { "item_id": 2, "received_qty": 100, "accepted_qty": 100, "rejected_qty": 0, "batch_number": "BATCH-002" }
  ]
}
```
This example deliberately receives less than what was ordered (a "partial"
delivery) -- so after this GRN, the PO's status will become `partial`, not
`completed`. Create a second GRN later with the remaining quantity to push it
to `completed`.

### Module 5 (early preview): Stock Ledger - read only (protected)

A minimal way to verify stock is updating correctly. Full reporting (stock
summary across all items, low stock alerts, valuation) comes later as part
of the dedicated Module 5 build-out.

| Method | Endpoint         | Description                              |
|--------|-------------------|--------------------------------------------|
| GET    | /stock/current    | Current stock balance for one item at one warehouse. Requires `?item_id=` and `?warehouse_id=` query params |
| GET    | /stock/ledger     | Raw transaction history (supports `?item_id=` and `?warehouse_id=` filters) |

### Module 3: BOM - Bill of Materials (protected)

A BOM is the "recipe" for a finished/semi-finished item: how much of each
raw material is needed to make ONE unit of it. Creating a new BOM for a
finished item automatically deactivates any previous active BOM for that
same item -- only one BOM should be active at a time, since Production
Orders always use the currently active BOM.

| Method | Endpoint                  | Description                              |
|--------|----------------------------|--------------------------------------------|
| POST   | /boms/                    | Create a new BOM/recipe for a finished item |
| GET    | /boms/                    | List BOMs (supports `?finished_item_id=`; `?active_only=` defaults to true) |
| GET    | /boms/{id}                | Get one BOM with full raw material breakdown |
| PATCH  | /boms/{id}/deactivate     | Manually deactivate a BOM                  |

**Example request body for `POST /boms/`:**
```json
{
  "finished_item_id": 3,
  "version": "1.0",
  "bom_items": [
    { "raw_item_id": 1, "qty_required": 2 },
    { "raw_item_id": 2, "qty_required": 0.5 }
  ]
}
```
This means: to make 1 unit of item #3, you need 2 units of item #1 and 0.5 units of item #2.

### Module 3: Production Orders (protected)

This is where raw material is actually consumed and finished goods are
created. A production order goes through: `planned` -> `in_progress` ->
`completed` (or `cancelled` at any point before completion).

| Method | Endpoint                              | Description                              |
|--------|------------------------------------------|--------------------------------------------|
| POST   | /production-orders/                      | Create a new order (status starts as `planned`) |
| GET    | /production-orders/                      | List orders (supports `?status=` and `?warehouse_id=`) |
| GET    | /production-orders/{id}                  | Get one order with full material issue / FG receipt / wastage breakdown |
| PATCH  | /production-orders/{id}/status           | Update status to `in_progress` or `cancelled` |
| POST   | /production-orders/{id}/complete         | **Completes the order -- this is what moves stock** |

**What happens automatically when you call `.../complete`:**
1. Calculates required raw material = `BOM.qty_required × actual_qty` for every raw material in the recipe.
2. Adds any wastage quantities on top of that.
3. **Checks stock availability first** -- if any raw material is short, the entire request is rejected with a clear error listing exactly which item(s) and how much is missing. Nothing is saved if there's a shortage.
4. Deducts raw material stock (`PRODUCTION_ISSUE`, one entry per raw material).
5. Deducts wastage stock (`WASTAGE`, if any was provided).
6. Adds finished goods stock (`FG_RECEIPT`) for `actual_qty`.
7. Marks the order `completed`.

**Example request body for `POST /production-orders/`:**
```json
{
  "order_number": "PROD-2026-001",
  "bom_id": 1,
  "warehouse_id": 1,
  "planned_qty": 100,
  "start_date": "2026-06-22"
}
```

**Example request body for `POST /production-orders/{id}/complete`:**
```json
{
  "actual_qty": 95,
  "end_date": "2026-06-22",
  "wastage": [
    { "item_id": 1, "wasted_qty": 3, "reason": "Cutting loss" }
  ]
}
```
Note `actual_qty` (95) can differ from the order's `planned_qty` (100) --
real production rarely matches the plan exactly, and the system uses
`actual_qty` (not planned_qty) for all stock calculations.

### Module 4: Sales Orders (protected)

Mirrors Purchase Orders, but for the outward (customer-facing) side. A
Sales Order by itself does NOT touch stock -- it just records "this customer
wants this." Stock is only deducted when a Dispatch Note is created against it.

| Method | Endpoint                  | Description                              |
|--------|----------------------------|--------------------------------------------|
| POST   | /sales-orders/             | Create a new SO with its line items (single request) |
| GET    | /sales-orders/             | List all SOs (supports `?status=` and `?customer_id=`) |
| GET    | /sales-orders/{id}         | Get one SO with full item details          |
| DELETE | /sales-orders/{id}         | Cancel a SO (sets status to "cancelled")  |

**Example request body for `POST /sales-orders/`:**
```json
{
  "so_number": "SO-2026-001",
  "customer_id": 1,
  "warehouse_id": 1,
  "items": [
    { "item_id": 3, "ordered_qty": 150, "rate": 80.00 }
  ]
}
```

### Module 4: Dispatch Notes (protected)

This is what actually deducts stock -- mirrors how GRN adds stock. Unlike
GRN, there's no quality-check split (no accepted/rejected) since this is
outgoing finished goods, not incoming raw material.

| Method | Endpoint           | Description                              |
|--------|---------------------|--------------------------------------------|
| POST   | /dispatch/          | Create a dispatch against a SO (deducts stock automatically) |
| GET    | /dispatch/          | List all dispatches (supports `?so_id=`)   |
| GET    | /dispatch/{id}      | Get one dispatch with full item details    |

**What happens automatically when you create a Dispatch Note:**
1. Validates the SO exists, and is not `cancelled` or already `completed`.
2. Validates every item in the dispatch actually belongs to that SO.
3. **Checks stock availability first** for every item -- if any item is short, the entire request is rejected with a clear error (nothing is saved). Same safety pattern used in production order completion.
4. Records a stock movement (`DISPATCH_OUT`, negative) for each item.
5. Re-checks the SO: if every line item's total dispatched quantity (across all dispatch notes so far) meets or exceeds what was ordered, the SO becomes `completed`; otherwise `partial`.

**Example request body for `POST /dispatch/`:**
```json
{
  "dispatch_number": "DSP-2026-001",
  "so_id": 1,
  "dispatch_date": "2026-06-22",
  "vehicle_number": "MH-15-AB-1234",
  "driver_name": "Ramesh Kumar",
  "items": [
    { "item_id": 3, "dispatched_qty": 120 }
  ]
}
```

### Module 5: Reports & Dashboard (protected, read-only)

All endpoints here are read-only -- they never change stock or any other
data, they just calculate and present what's already in `stock_ledger`,
`items`, `grn`, etc.

| Method | Endpoint                      | Description                              |
|--------|----------------------------------|--------------------------------------------|
| GET    | /reports/stock-summary           | Current stock for every item at every warehouse, with average rate and stock value. Supports `?warehouse_id=`, `?category=`, `?only_in_stock=` (default true) |
| GET    | /reports/low-stock                | Items currently below their `min_stock_level`, sorted by worst shortfall first. Supports `?warehouse_id=` |
| GET    | /reports/stock-valuation          | Total stock value across the factory, broken down by warehouse |
| GET    | /reports/consumption               | Total quantity consumed per item (production issue + dispatch + wastage combined). Supports `?warehouse_id=` |
| GET    | /reports/supplier-purchases        | Total accepted quantity purchased per supplier, across all their GRNs |

**How stock valuation works:** Each item's value is `current_stock × average_rate`,
where `average_rate` is the **weighted average** purchase rate calculated
across all GRN line items for that item (`sum(accepted_qty × rate) / sum(accepted_qty)`,
where `rate` comes from the linked Purchase Order's line item). This is the
standard "Weighted Average Cost" inventory valuation method. If an item has
never been received via any GRN (e.g. a finished good that only comes from
production), its average rate is `0`.

**Performance note:** `get_average_rate()` runs one query per item (called
once per row in `/reports/stock-summary` and `/reports/stock-valuation`).
This is fine for the current data volumes (tens to low hundreds of items),
but if the item catalog grows into the thousands, this should be refactored
into a single batched query rather than one query per item.

## How to test the full login flow

**IMPORTANT CHANGE:** `/auth/login` now expects **form-data** (not JSON), with
the email entered in a field called `username` (this is the OAuth2 standard
field name -- even though we're putting an email in it). This change was made
so that Swagger's green "Authorize" button works directly, instead of giving
a 422 error.

### Option 1: Using the Swagger UI (easiest, and now works with "Authorize")
1. Open `http://127.0.0.1:8000/docs`
2. Expand `GET /roles/`, click "Try it out" -> "Execute" to see the list of roles and their ids
3. Expand `POST /auth/register`, click "Try it out", and create a user with the `role_id` you want (e.g. Admin's id)
4. Click the green **"Authorize"** button at the top right of the page
5. In the popup, enter your **email** in the "username" field and your password in the "password" field, then click Authorize
6. Now all `/items/`, `/warehouses/`, `/suppliers/`, `/customers/` endpoints will work directly from this page -- no need to manually copy/paste any token

### Option 2: Using curl
```bash
# 0. Check available roles first
curl http://127.0.0.1:8000/roles/
# Response: [{"id": 1, "name": "Admin"}, {"id": 2, "name": "Store Manager"}, ...]

# 1. Register a user (use the Admin role's id from step 0)
curl -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name": "Rahul Sharma", "email": "rahul@factory.com", "password": "secret123", "role_id": 1}'

# 2. Login to get a token -- NOTE: this is now form-data, not JSON
curl -X POST http://127.0.0.1:8000/auth/login \
  -d "username=rahul@factory.com&password=secret123"
# Response: {"access_token": "eyJ...", "token_type": "bearer"}

# 3. Use the token to access a protected route
curl http://127.0.0.1:8000/items/ \
  -H "Authorization: Bearer eyJ...(paste full token here)"
```

### How the React frontend should call /auth/login

```javascript
const body = new URLSearchParams();
body.append('username', email);   // field must be named "username", even though it's an email
body.append('password', password);

const res = await fetch('http://127.0.0.1:8000/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body,
});
const data = await res.json();
// data.access_token -> store this (e.g. in memory / context, not localStorage for production)
```

## Next Steps (to be built next)

- Stock Transfer between warehouses (multi-location support)
- Module 9-12 (advanced features): Barcode/QR scanning, notifications, Excel/PDF export
- React frontend build-out
