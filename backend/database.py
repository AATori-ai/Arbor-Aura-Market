from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from models import Base, Category, Municipality, User, Listing
from auth import hash_password

from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite:///tori.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        # Expired boost cleanup logic
        db.query(Listing).filter(
            Listing.boost_expires.isnot(None),
            Listing.boost_expires < datetime.utcnow()
        ).update({
            Listing.boost_type: "Free",
            Listing.is_featured: 0,
            Listing.boost_expires: None
        }, synchronize_session=False)
        db.commit()
    except Exception as e:
        print(f"Error cleaning up expired boosts: {e}")
        db.rollback()

    try:
        yield db
    finally:
        db.close()



def seed():
    db = Session(engine)
    try:
        Base.metadata.create_all(bind=engine)

        # --- Categories ---
        if db.query(Category).count() < 9:
            cats_data = [
                ("electronics", "Elektroniikka", "Electronics", "📱", None),
                ("vehicles", "Ajoneuvot", "Vehicles", "🚗", None),
                ("home", "Koti & Puutarha", "Home & Garden", "🛋️", None),
                ("fashion", "Muoti", "Fashion", "👗", None),
                ("sports", "Urheilu", "Sports", "⚽", None),
                ("kids", "Lapset", "Kids", "🧸", None),
                ("books", "Kirjat", "Books", "📚", None),
                ("services", "Palvelut", "Services", "🔧", None),
                ("pets", "Lemmikit", "Pets", "🐾", None),
            ]
            for slug, nf, ne, em, pid in cats_data:
                db.add(Category(slug=slug, name_fi=nf, name_en=ne, emoji=em, parent_id=pid))
            db.flush()

            # --- Subcategories ---
            cat_map = {c.slug: c.id for c in db.query(Category).all()}
            subs = [
                # Electronics subcategories
                ("phones", "Puhelimet", "Phones", "📱", "electronics"),
                ("computers", "Tietokoneet", "Computers", "💻", "electronics"),
                ("audio", "Ääni & Viihde", "Audio & Video", "🎵", "electronics"),
                ("cameras", "Kamerat", "Cameras", "📷", "electronics"),
                ("games", "Videopelit", "Video Games", "🎮", "electronics"),
                ("home-appliances", "Kodinkoneet", "Home Appliances", "🔌", "electronics"),
                # Vehicles subcategories
                ("car-parts", "Auton osat", "Car Parts", "🔧", "vehicles"),
                ("car-accessories", "Autotarvikkeet", "Car Accessories", "🧰", "vehicles"),
                ("bikes", "Polkupyörät", "Bicycles", "🚲", "vehicles"),
                ("boats", "Veneet", "Boats", "⛵", "vehicles"),
                # Home subcategories
                ("furniture", "Huonekalut", "Furniture", "🛋️", "home"),
                ("garden", "Puutarha", "Garden", "🌱", "home"),
                ("tools", "Työkalut", "Tools", "🔨", "home"),
                ("kitchen", "Keittiö", "Kitchen", "🍳", "home"),
                # Fashion subcategories
                ("womens", "Naisten vaatteet", "Women's Clothing", "👗", "fashion"),
                ("mens", "Miesten vaatteet", "Men's Clothing", "👔", "fashion"),
                ("jewelry", "Korut", "Jewelry", "💍", "fashion"),
                ("shoes", "Kengät", "Shoes", "👟", "fashion"),
                # Sports subcategories
                ("fitness", "Kuntoilu", "Fitness", "🏋️", "sports"),
                ("outdoor", "Retkeily", "Outdoor", "🏕️", "sports"),
                ("winter", "Talviurheilu", "Winter Sports", "⛷️", "sports"),
                # Kids subcategories
                ("toys", "Lelut", "Toys", "🧸", "kids"),
                ("baby-gear", "Vauvatarvikkeet", "Baby Gear", "👶", "kids"),
                ("kids-clothing", "Lasten vaatteet", "Kids Clothing", "👕", "kids"),
            ]
            for slug, nf, ne, em, parent_slug in subs:
                pid = cat_map.get(parent_slug)
                if pid and not db.query(Category).filter(Category.slug == slug).first():
                    db.add(Category(slug=slug, name_fi=nf, name_en=ne, emoji=em, parent_id=pid))
            db.flush()

        # --- Municipalities ---
        if db.query(Municipality).count() < 10:
            finnish_cities = [
                "Askola", "Espoo", "Hanko", "Helsinki", "Hyvinkää", "Inkoo", "Järvenpää",
                "Karkkila", "Kauniainen", "Kerava", "Kirkkonummi", "Lapinjärvi", "Lohja",
                "Loviisa", "Myrskylä", "Mäntsälä", "Nurmijärvi", "Pornainen", "Porvoo",
                "Pukkila", "Raasepori", "Sipoo", "Siuntio", "Tuusula", "Vantaa", "Vihti",
                "Aura", "Kaarina", "Kemiönsaari", "Koski Tl", "Kustavi", "Laitila", "Lieto",
                "Loimaa", "Marttila", "Masku", "Mynämäki", "Naantali", "Nousiainen",
                "Oripää", "Paimio", "Parainen", "Pyhäranta", "Pöytyä", "Raisio", "Rusko",
                "Salo", "Sauvo", "Somero", "Taivassalo", "Turku", "Uusikaupunki", "Vehmaa",
                "Eura", "Eurajoki", "Harjavalta", "Huittinen", "Jämijärvi", "Kankaanpää",
                "Karvia", "Kokemäki", "Merikarvia", "Nakkila", "Pomarkku", "Pori", "Rauma",
                "Siikainen", "Säkylä", "Ulvila", "Forssa", "Hattula", "Hausjärvi",
                "Humppila", "Hämeenlinna", "Janakkala", "Jokioinen", "Loppi", "Riihimäki",
                "Tammela", "Ypäjä", "Akaa", "Hämeenkyrö", "Ikaalinen", "Juupajoki",
                "Kangasala", "Kihniö", "Lempäälä", "Mänttä-Vilppula", "Nokia", "Orivesi",
                "Parkano", "Pirkkala", "Punkalaidun", "Pälkäne", "Ruovesi", "Sastamala",
                "Tampere", "Urjala", "Valkeakoski", "Vesilahti", "Virrat", "Ylöjärvi",
                "Asikkala", "Hartola", "Heinola", "Hollola", "Iitti", "Kärkölä", "Lahti",
                "Orimattila", "Padasjoki", "Sysmä", "Hamina", "Kotka", "Kouvola",
                "Miehikkälä", "Pyhtää", "Virolahti", "Imatra", "Lappeenranta", "Lemi",
                "Luumäki", "Parikkala", "Rautjärvi", "Ruokolahti", "Savitaipale",
                "Taipalsaari", "Enonkoski", "Heinävesi", "Hirvensalmi", "Joroinen", "Juva",
                "Kangasniemi", "Mikkeli", "Mäntyharju", "Pertunmaa", "Pieksämäki", "Puumala",
                "Rantasalmi", "Savonlinna", "Sulkava", "Iisalmi", "Kaavi", "Keitele",
                "Kiuruvesi", "Kuopio", "Lapinlahti", "Leppävirta", "Pielavesi", "Rautalampi",
                "Rautavaara", "Siilinjärvi", "Sonkajärvi", "Suonenjoki", "Tervo", "Tuusniemi",
                "Varkaus", "Vesanto", "Vieremä", "Ilomantsi", "Joensuu", "Juuka", "Kitee",
                "Kontiolahti", "Lieksa", "Liperi", "Nurmes", "Outokumpu", "Polvijärvi",
                "Rääkkylä", "Tohmajärvi", "Valtimo", "Hankasalmi", "Joutsa", "Jyväskylä",
                "Jämsä", "Kannonkoski", "Karstula", "Keuruu", "Kinnula", "Kivijärvi",
                "Konnevesi", "Kuhmoinen", "Kyyjärvi", "Laukaa", "Luhanka", "Multia",
                "Muurame", "Petäjävesi", "Pihtipudas", "Saarijärvi", "Toivakka", "Uurainen",
                "Viitasaari", "Äänekoski", "Alajärvi", "Alavus", "Evijärvi", "Ilmajoki",
                "Isojoki", "Isokyrö", "Karijoki", "Kauhajoki", "Kauhava", "Kuortane",
                "Kurikka", "Lappajärvi", "Lapua", "Seinäjoki", "Soini", "Teuva", "Vimpeli",
                "Ähtäri", "Kaskinen", "Korsnäs", "Kristiinankaupunki", "Kruunupyy", "Laihia",
                "Luoto", "Maalahti", "Mustasaari", "Närpiö", "Pedersöre", "Pietarsaari",
                "Uusikaarlepyy", "Vaasa", "Vöyri", "Halsua", "Kannus", "Kaustinen", "Kokkola",
                "Lestijärvi", "Perho", "Toholampi", "Veteli", "Alavieska", "Haapajärvi",
                "Haapavesi", "Hailuoto", "Ii", "Kalajoki", "Kempele", "Kuusamo", "Kärsämäki",
                "Liminka", "Lumijoki", "Merijärvi", "Muhos", "Nivala", "Oulainen", "Oulu",
                "Pyhäjoki", "Pyhäjärvi", "Pyhäntä", "Raahe", "Reisjärvi", "Sievi", "Siikajoki",
                "Siikalatva", "Taivalkoski", "Tyrnävä", "Utajärvi", "Vaala", "Vihanti",
                "Ylivieska", "Hyrynsalmi", "Kajaani", "Kuhmo", "Paltamo", "Puolanka",
                "Ristijärvi", "Sotkamo", "Suomussalmi", "Enontekiö", "Inari", "Kemi",
                "Kemijärvi", "Keminmaa", "Kittilä", "Kolari", "Muonio", "Pelkosenniemi",
                "Pello", "Posio", "Ranua", "Rovaniemi", "Salla", "Savukoski", "Simo",
                "Sodankylä", "Tervola", "Tornio", "Utsjoki", "Ylitornio",
                "Brändö", "Eckerö", "Finström", "Föglö", "Geta", "Hammarland", "Jomala",
                "Kumlinge", "Kökar", "Lemland", "Lumparland", "Maarianhamina", "Saltvik",
                "Sottunga", "Sund", "Vårdö",
            ]
            for city in sorted(set(finnish_cities), key=lambda x: x.lower()):
                db.add(Municipality(name_fi=city, name_en=city))
            db.flush()

        # --- Admin user ---
        if not db.query(User).filter(User.email == "contact@arboraura.fi").first():
            db.add(User(
                email="contact@arboraura.fi",
                password_hash=hash_password("admin123"),
                full_name="Admin User",
                role="admin",
            ))
            db.flush()

        # --- Demo user ---
        if not db.query(User).filter(User.email == "demo@arboraura.fi").first():
            demo = User(
                email="demo@arboraura.fi",
                password_hash=hash_password("demo123"),
                full_name="Demo User",
                role="user",
            )
            db.add(demo)
            db.flush()

            # --- Demo approved listings ---
            electronics_cat = db.query(Category).filter(Category.slug == "electronics").first()
            home_cat = db.query(Category).filter(Category.slug == "home").first()
            sports_cat = db.query(Category).filter(Category.slug == "sports").first()
            vehicles_cat = db.query(Category).filter(Category.slug == "vehicles").first()
            fashion_cat = db.query(Category).filter(Category.slug == "fashion").first()
            kids_cat = db.query(Category).filter(Category.slug == "kids").first()
            pets_cat = db.query(Category).filter(Category.slug == "pets").first()

            demo_listings = [
                {"title_fi": "iPhone 14 Pro 256GB — Avaruusmusta", "title_en": "iPhone 14 Pro 256GB — Space Black", "price": 649, "location": "Helsinki", "condition": "Kuin uusi", "category_id": electronics_cat.id, "is_featured": 1, "description": "Käytetty 6 kuukautta. Ei naarmuja."},
                {"title_fi": "Maantiepyörä Trek FX 3 Disc 2022", "title_en": "Road bike Trek FX 3 Disc 2022", "price": 890, "location": "Tampere", "condition": "Kuin uusi", "category_id": sports_cat.id, "is_featured": 1, "description": "Vain 200 km ajettu."},
                {"title_fi": "MacBook Air M2 13\" — sinetöity", "title_en": "MacBook Air M2 13\" — sealed", "price": 999, "location": "Vantaa", "condition": "Uusi", "category_id": electronics_cat.id, "description": "Avaamaton pakkaus."},
                {"title_fi": "IKEA SÖDERHAMN kulmasohva", "title_en": "IKEA SÖDERHAMN corner sofa", "price": 320, "location": "Espoo", "condition": "Hyvä", "category_id": home_cat.id, "description": "3,5 vuotta vanha, ei vaurioita."},
                {"title_fi": "Nikon Z6 II runko + 24-70mm f/4", "title_en": "Nikon Z6 II body + 24-70mm f/4", "price": 1750, "location": "Oulu", "condition": "Hyvä", "category_id": electronics_cat.id, "is_featured": 1, "description": "Täyskehosensori. Vain 12K laukauksia."},
                {"title_fi": "Talvirengassarja 205/55 R16", "title_en": "Winter tyre set 205/55 R16", "price": 220, "location": "Oulu", "condition": "Hyvä", "category_id": vehicles_cat.id, "description": "3 talven käyttö."},
                {"title_fi": "Vintage Marimekko Unikko-mekko", "title_en": "Vintage Marimekko Unikko dress", "price": 75, "location": "Turku", "condition": "Hyvä", "category_id": fashion_cat.id, "description": "Klassinen unikko-printti."},
                {"title_fi": "LEGO Technic Ferrari Daytona SP3", "title_en": "LEGO Technic Ferrari Daytona SP3", "price": 280, "location": "Helsinki", "condition": "Kuin uusi", "category_id": kids_cat.id, "description": "Koottu kerran."},
                {"title_fi": "PS5-konsoli + 2 ohjainta + 6 peliä", "title_en": "PS5 console + 2 controllers + 6 games", "price": 520, "location": "Espoo", "condition": "Hyvä", "category_id": electronics_cat.id, "description": "Levy-versio monilla peleillä."},
                {"title_fi": "Sähkösäätöpöytä FLEXISPOT E7", "title_en": "Electric sit-stand desk FLEXISPOT E7", "price": 340, "location": "Tampere", "condition": "Hyvä", "category_id": home_cat.id, "description": "Muistiasetukset, korkeus 62-125 cm."},
            ]
            for ld in demo_listings:
                db.add(Listing(
                    user_id=demo.id,
                    category_id=ld["category_id"],
                    title_fi=ld["title_fi"],
                    title_en=ld["title_en"],
                    price=ld["price"],
                    location=ld["location"],
                    condition=ld["condition"],
                    description=ld.get("description", ""),
                    status="approved",
                    is_featured=ld.get("is_featured", 0),
                    boost_type="Featured" if ld.get("is_featured") else "Free",
                ))
            db.flush()

        db.commit()
    except Exception as e:
        print(f"Seed error (may be OK if tables already exist): {e}")
        db.rollback()
    finally:
        db.close()
