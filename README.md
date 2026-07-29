# FMMS Simple

Ek bohot simple Factory Material Management backend — sirf 6 cheezein:

1. **Item** — Raw Material aur Product ki master list
2. **Raw Material In** — Kacha maal factory mein aaya (stock IN)
3. **Stock (Production)** — Raw material use karke product banaya (raw OUT + product IN)
4. **Out Material** — Maal factory se bahar gaya (stock OUT)
5. **Return Material** — Maal wapas aaya (stock IN)
6. **Available Material** — Abhi kitna stock pada hai (report)

Auth, Warehouse, Supplier, Customer, PO, SO, BOM — sab hata diya gaya hai. Agar baad mein chahiye ho to alag se add kiya ja sakta hai.

## Run Karne Ke Liye (Backend)

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

Backend chalu hoga: **http://127.0.0.1:8000**
Swagger docs (API test karne ke liye): **http://127.0.0.1:8000/docs**

Database automatically ban jaayega: `fmms_simple.db` (SQLite file).

## Frontend (index.html)

`index.html` ko seedha **double-click** karke browser mein khol do — ye direct
real backend API se connect hota hai (fetch calls), koi build step nahi chahiye.

- Backend pehle chalu hona chahiye (`uvicorn main:app --reload`).
- Agar backend kisi doosre URL/port par chal raha hai, sidebar ke sabse neeche
  wale input box mein API URL change kar do (default: `http://127.0.0.1:8000`).
- Sidebar mein "API Connected" (green dot) dikhna chahiye — agar red dot dikhe
  to matlab backend chalu nahi hai ya URL galat hai.

Frontend mein ye pages hain: Available Material (dashboard), Item, Raw Material In,
Stock (Production), Out Material, Return Material -- har page ka apna form hai
jo turant real database mein save/update karta hai.

## API List

| Module | Method | URL |
|---|---|---|
| Item | POST | `/items/` |
| Item | GET | `/items/` |
| Item | GET | `/items/{id}` |
| Item | PUT | `/items/{id}` |
| Item | DELETE | `/items/{id}` |
| Raw Material In | POST | `/raw-material-in/` |
| Raw Material In | GET | `/raw-material-in/` |
| Stock (Production) | POST | `/production/` |
| Stock (Production) | GET | `/production/` |
| Out Material | POST | `/out-material/` |
| Out Material | GET | `/out-material/` |
| Return Material | POST | `/return-material/` |
| Return Material | GET | `/return-material/` |
| Available Material | GET | `/available-material/` |
| Available Material | GET | `/available-material/{item_id}` |

## Example Flow

```
1. POST /items/           -> "Wood Plank" (raw_material) banao
2. POST /items/           -> "Wooden Chair" (product) banao
3. POST /raw-material-in/ -> 500 Wood Plank stock mein add karo
4. POST /production/      -> 100 Wood Plank use karke 20 Wooden Chair banao
5. POST /out-material/    -> 5 Chair bahar bheje (sale)
6. POST /return-material/ -> 2 Chair wapas aaye
7. GET  /available-material/ -> current stock dekho
```

## Important Logic

- Stock hamesha `Item.current_stock` field mein directly maintained hai (fast & simple).
- Har transaction `stock_transactions` table mein bhi log hoti hai (history/audit ke liye).
- Agar stock kam ho aur koi **Out Material** ya **Production (consume)** karne ki koshish kare, request turant reject ho jaati hai (`400 error`) — negative stock kabhi nahi banega.
