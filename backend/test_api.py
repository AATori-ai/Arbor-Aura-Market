import json
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8000/api"

def req(method, path, data=None, token=None):
    url = BASE + path
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data else None
    r = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(r)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return {"error": e.code, "detail": e.read().decode()}

def test():
    print("=== AA_Tori API Tests ===")

    # Health
    h = req("GET", "/health")
    print(f"[HEALTH] {h}")
    assert h["status"] == "ok"

    # Register
    r = req("POST", "/auth/register", {"email": "test@test.com", "password": "Test1234", "full_name": "Test User"})
    print(f"[REGISTER] user_id={r.get('user_id')} role={r.get('role')}")
    token = r.get("access_token", "")
    assert token

    # Duplicate register
    r = req("POST", "/auth/register", {"email": "test@test.com", "password": "Test1234"})
    print(f"[DUP REGISTER] {r.get('detail','ok')}")

    # Login
    r = req("POST", "/auth/login", {"email": "test@test.com", "password": "Test1234"})
    print(f"[LOGIN] user_id={r.get('user_id')} role={r.get('role')}")
    token = r.get("access_token", "")

    # Get me
    r = req("GET", "/auth/me", token=token)
    print(f"[ME] {r.get('email')} role={r.get('role')}")

    # Categories
    cats = req("GET", "/categories")
    print(f"[CATEGORIES] {len(cats)} categories retrieved")

    # Municipalities
    mun = req("GET", "/municipalities")
    print(f"[MUNICIPALITIES] {len(mun)} municipalities retrieved")

    # Create listing
    listing_data = {
        "title_fi": "Testi iPhone 14 Pro",
        "title_en": "Test iPhone 14 Pro",
        "category_id": cats[0]["id"] if cats else 1,
        "condition": "Hyvä",
        "price": 299.0,
        "location": "Helsinki",
        "description": "Test listing from test script",
        "boost_type": "Free"
    }
    l = req("POST", "/listings", listing_data, token=token)
    print(f"[CREATE LISTING] id={l.get('id')} status={l.get('status')}")
    listing_id = l.get("id")
    assert listing_id
    assert l["status"] == "pending"

    # Get my listings
    my = req("GET", "/listings/my", token=token)
    print(f"[MY LISTINGS] {len(my)} listings")

    # Public listings (should be empty since pending)
    pub = req("GET", "/listings")
    before = len(pub)
    print(f"[PUBLIC LISTINGS] {before} public listings (pending not shown)")

    # Admin login
    r = req("POST", "/auth/login", {"email": "admin@arboraura.fi", "password": "admin123"})
    print(f"[ADMIN LOGIN] user_id={r.get('user_id')} role={r.get('role')}")
    admin_token = r.get("access_token", "")
    assert r.get("role") == "admin"

    # Admin stats
    stats = req("GET", "/admin/stats", token=admin_token)
    print(f"[ADMIN STATS] pending={stats.get('pending_listings')} total={stats.get('total_listings')} users={stats.get('total_users')}")

    # Admin pending listings
    pending = req("GET", "/admin/listings?status=pending", token=admin_token)
    print(f"[ADMIN PENDING] {len(pending)} pending listings")

    # Admin approve listing
    if pending:
        pid = pending[0]["id"]
        ap = req("PUT", f"/admin/listings/{pid}/approve", token=admin_token)
        print(f"[APPROVE] listing {pid} -> status={ap.get('status')}")

        # Public listings should now include it
        pub = req("GET", "/listings")
        print(f"[PUBLIC AFTER APPROVE] {len(pub)} public listings")

        # Favorites
        fav = req("POST", f"/favorites/{pid}", token=token)
        print(f"[FAVORITE] {fav.get('message')}")

        favs = req("GET", "/favorites", token=token)
        print(f"[LIST FAVORITES] {len(favs)} favorites")

        # Remove favorite
        unfav = req("DELETE", f"/favorites/{pid}", token=token)
        print(f"[UNFAVORITE] {unfav.get('message')}")

    # Contact form
    c = req("POST", "/contact", {"name": "Test User", "email": "test@test.com", "subject": "Test", "message": "This is a test message"})
    print(f"[CONTACT] {c.get('message')}")

    # Admin contacts
    contacts = req("GET", "/admin/contacts", token=admin_token)
    print(f"[ADMIN CONTACTS] {len(contacts)} contacts")

    # Admin listings (all)
    all_list = req("GET", "/admin/listings?status=all", token=admin_token)
    print(f"[ADMIN ALL LISTINGS] {len(all_list)} total")

    # Admin users
    users = req("GET", "/admin/users", token=admin_token)
    print(f"[ADMIN USERS] {len(users)} users")

    # Public stats
    stats_pub = req("GET", "/stats")
    print(f"[PUBLIC STATS] {stats_pub}")

    # GDPR Tests
    print("\n=== GDPR TESTS ===")
    import time
    gdpr_email = f"gdpr_{int(time.time())}@test.com"
    gdpr_reg = req("POST", "/auth/register", {"email": gdpr_email, "password": "Password123", "full_name": "GDPR User"})
    gdpr_token = gdpr_reg.get("access_token", "")
    assert gdpr_token, "GDPR test user registration failed"
    print(f"[GDPR REGISTER] user_id={gdpr_reg.get('user_id')}")

    # Export GDPR data
    export_res = req("GET", "/gdpr/export", token=gdpr_token)
    print(f"[GDPR EXPORT] profile email={export_res.get('profile', {}).get('email')}")
    assert export_res.get("profile", {}).get("email") == gdpr_email
    assert "listings" in export_res
    assert "saved_listings" in export_res
    assert "conversations" in export_res

    # Delete GDPR data
    delete_res = req("DELETE", "/gdpr/delete", token=gdpr_token)
    print(f"[GDPR DELETE] response={delete_res}")
    assert "Account deleted successfully" in delete_res.get("detail", "")

    # Try to access profile again (should fail)
    me_res = req("GET", "/auth/me", token=gdpr_token)
    print(f"[GDPR VERIFY DELETED] GET /auth/me -> {me_res.get('error') or me_res.get('detail')}")
    assert me_res.get("error") is not None or "not found" in str(me_res.get("detail", "")).lower()

    print("=== GDPR TESTS PASSED ===\n")

    print("\n=== ALL TESTS PASSED ===")

if __name__ == "__main__":
    test()
