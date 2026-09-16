import os
import math
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SECRET_KEY = os.getenv("SECRET_KEY", "nexcare-demo-secret-change-me")
DATA_MODE = os.getenv("DATA_MODE", "mock").lower()

# MySQL Database Configuration
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DB = os.getenv("MYSQL_DB", "nexcare")

# Configurable Demo Crowd Thresholds
# Green = Low (total current + waiting <= 40)
# Yellow = Moderate (total current + waiting <= 80)
# Red = High (total current + waiting > 80)
CROWD_THRESHOLDS = {
    "low_max": 40,
    "moderate_max": 80
}

# 12 Primary Supported Chennai Localities
AREAS = [
    "Tambaram",
    "Guindy",
    "Velachery",
    "Adyar",
    "Anna Nagar",
    "T. Nagar",
    "Porur",
    "Sholinganallur",
    "Perambur",
    "Egmore",
    "Mogappair",
    "Manapakkam"
]

# Approximate Geographic Coordinates for Chennai Localities (Latitude, Longitude)
LOCALITY_COORDINATES = {
    "Tambaram": (12.9249, 80.1000),
    "Guindy": (13.0067, 80.2025),
    "Velachery": (12.9815, 80.2180),
    "Adyar": (13.0012, 80.2565),
    "Anna Nagar": (13.0850, 80.2101),
    "T. Nagar": (13.0418, 80.2341),
    "Porur": (13.0382, 80.1565),
    "Sholinganallur": (12.9010, 80.2279),
    "Perambur": (13.1075, 80.2337),
    "Egmore": (13.0827, 80.2600),
    "Mogappair": (13.0878, 80.1706),
    "Manapakkam": (13.0180, 80.1800),
}

# Extensive Indian States & Union Territories hierarchy with major cities / localities
INDIA_LOCATIONS = {
    "Tamil Nadu": [
        "Chennai - Adyar", "Chennai - Anna Nagar", "Chennai - Egmore", "Chennai - Guindy",
        "Chennai - Manapakkam", "Chennai - Mogappair", "Chennai - Perambur", "Chennai - Porur",
        "Chennai - Sholinganallur", "Chennai - T. Nagar", "Chennai - Tambaram", "Chennai - Velachery",
        "Coimbatore", "Madurai", "Tiruchirappalli", "Salem", "Tirunelveli", "Vellore", "Erode"
    ],
    "Kerala": [
        "Thiruvananthapuram", "Kochi", "Kozhikode", "Thrissur", "Kollam", "Kannur",
        "Alappuzha", "Palakkad", "Kottayam", "Malappuram"
    ],
    "Karnataka": [
        "Bengaluru - Old Airport Road", "Bengaluru - Kalasipalya", "Bengaluru - Bommasandra",
        "Bengaluru - Shivaji Nagar", "Bengaluru - Bannerghatta Road", "Bengaluru - Koramangala",
        "Bengaluru", "Mysuru", "Mangaluru", "Hubballi-Dharwad", "Belagavi", "Shivamogga", "Ballari"
    ],
    "Andhra Pradesh": [
        "Visakhapatnam", "Vijayawada", "Guntur", "Nellore", "Kurnool", "Tirupati", "Kakinada"
    ],
    "Telangana": [
        "Hyderabad", "Warangal", "Nizamabad", "Khammam", "Karimnagar"
    ],
    "Maharashtra": [
        "Mumbai", "Pune", "Nagpur", "Thane", "Nashik", "Aurangabad", "Solapur"
    ],
    "Delhi (NCT)": [
        "New Delhi", "Central Delhi", "South Delhi", "North Delhi", "East Delhi", "West Delhi"
    ],
    "Gujarat": [
        "Ahmedabad", "Surat", "Vadodara", "Rajkot", "Bhavnagar", "Jamnagar"
    ],
    "West Bengal": [
        "Kolkata", "Howrah", "Durgapur", "Asansol", "Siliguri"
    ],
    "Rajasthan": [
        "Jaipur", "Jodhpur", "Kota", "Bikaner", "Ajmer", "Udaipur"
    ],
    "Uttar Pradesh": [
        "Lucknow", "Kanpur", "Varanasi", "Agra", "Prayagraj", "Noida", "Ghaziabad"
    ],
    "Madhya Pradesh": [
        "Bhopal", "Indore", "Jabalpur", "Gwalior", "Ujjain"
    ],
    "Bihar": [
        "Patna", "Gaya", "Bhagalpur", "Muzaffarpur"
    ],
    "Punjab": [
        "Chandigarh", "Ludhiana", "Amritsar", "Jalandhar", "Patiala"
    ],
    "Haryana": [
        "Gurugram", "Faridabad", "Panipat", "Ambala"
    ],
    "Odisha": [
        "Bhubaneswar", "Cuttack", "Rourkela", "Puri", "Sambalpur"
    ],
    "Assam": [
        "Guwahati", "Silchar", "Dibrugarh", "Jorhat"
    ],
    "Goa": [
        "Panaji", "Margao", "Vasco da Gama"
    ],
    "Puducherry": [
        "Puducherry", "Karaikal", "Mahe", "Yanam"
    ]
}

# Extended Coordinates for all-India cities for distance calculations to Chennai
ALL_INDIA_COORDINATES = {
    # Chennai localities
    **LOCALITY_COORDINATES,
    "Chennai - Adyar": (13.0012, 80.2565),
    "Chennai - Anna Nagar": (13.0850, 80.2101),
    "Chennai - Egmore": (13.0827, 80.2600),
    "Chennai - Guindy": (13.0067, 80.2025),
    "Chennai - Manapakkam": (13.0180, 80.1800),
    "Chennai - Mogappair": (13.0878, 80.1706),
    "Chennai - Perambur": (13.1075, 80.2337),
    "Chennai - Porur": (13.0382, 80.1565),
    "Chennai - Sholinganallur": (12.9010, 80.2279),
    "Chennai - T. Nagar": (13.0418, 80.2341),
    "Chennai - Tambaram": (12.9249, 80.1000),
    "Chennai - Velachery": (12.9815, 80.2180),
    
    # Tamil Nadu cities
    "Coimbatore": (11.0168, 76.9558),
    "Madurai": (9.9252, 78.1198),
    "Tiruchirappalli": (10.7905, 78.7047),
    "Salem": (11.6643, 78.1460),
    "Tirunelveli": (8.7139, 77.7567),
    "Vellore": (12.9165, 79.1325),
    "Erode": (11.3410, 77.7172),

    # Kerala
    "Thiruvananthapuram": (8.5241, 76.9366),
    "Kochi": (9.9312, 76.2673),
    "Kozhikode": (11.2588, 75.7804),
    "Thrissur": (10.5276, 76.2144),
    "Kollam": (8.8932, 76.6141),
    "Kannur": (11.8745, 75.3704),
    "Alappuzha": (9.4981, 76.3388),
    "Palakkad": (10.7867, 76.6548),
    "Kottayam": (9.5916, 76.5222),

    # Karnataka
    "Bengaluru": (12.9716, 77.5946),
    "Bengaluru - Central": (12.9716, 77.5946),
    "Bengaluru - Old Airport Road": (12.9587, 77.6483),
    "Bengaluru - Kalasipalya": (12.9628, 77.5752),
    "Bengaluru - Bommasandra": (12.8173, 77.6917),
    "Bengaluru - Shivaji Nagar": (12.9822, 77.6047),
    "Bengaluru - Bannerghatta Road": (12.8943, 77.5985),
    "Bengaluru - Koramangala": (12.9317, 77.6186),
    "Old Airport Road": (12.9587, 77.6483),
    "Kalasipalya": (12.9628, 77.5752),
    "Bommasandra": (12.8173, 77.6917),
    "Shivaji Nagar": (12.9822, 77.6047),
    "Bannerghatta Road": (12.8943, 77.5985),
    "Koramangala": (12.9317, 77.6186),
    "Mysuru": (12.2958, 76.6394),
    "Mangaluru": (12.9141, 74.8560),
    "Hubballi-Dharwad": (15.3647, 75.1240),

    # Andhra Pradesh & Telangana
    "Visakhapatnam": (17.6868, 83.2185),
    "Vijayawada": (16.5062, 80.6480),
    "Tirupati": (13.6288, 79.4192),
    "Hyderabad": (17.3850, 78.4867),
    "Warangal": (17.9689, 79.5941),

    # Other Major Indian Hubs & States
    "Mumbai": (19.0760, 72.8777),
    "Pune": (18.5204, 73.8567),
    "Nagpur": (21.1458, 79.0882),
    "Thane": (19.2183, 72.9781),
    "New Delhi": (28.6139, 77.2090),
    "Central Delhi": (28.6448, 77.2167),
    "South Delhi": (28.5355, 77.2410),
    "North Delhi": (28.7041, 77.1025),
    "East Delhi": (28.6279, 77.2955),
    "West Delhi": (28.6562, 77.0784),
    "Kolkata": (22.5726, 88.3639),
    "Howrah": (22.5958, 88.2636),
    "Ahmedabad": (23.0225, 72.5714),
    "Surat": (21.1702, 72.8311),
    "Vadodara": (22.3072, 73.1812),
    "Jaipur": (26.9124, 75.7873),
    "Jodhpur": (26.2389, 73.0243),
    "Lucknow": (26.8467, 80.9462),
    "Kanpur": (26.4499, 80.3319),
    "Varanasi": (25.3176, 82.9739),
    "Noida": (28.5355, 77.3910),
    "Bhopal": (23.2599, 77.4126),
    "Indore": (22.7196, 75.8577),
    "Patna": (25.5941, 85.1376),
    "Gaya": (24.7914, 85.0002),
    "Chandigarh": (30.7333, 76.7794),
    "Ludhiana": (30.9010, 75.8573),
    "Gurugram": (28.4595, 77.0266),
    "Faridabad": (28.4089, 77.3178),
    "Bhubaneswar": (20.2961, 85.8245),
    "Cuttack": (20.4625, 85.8830),
    "Guwahati": (26.1445, 91.7362),
    "Panaji": (15.4909, 73.8278),
    "Margao": (15.2832, 73.9862),
    "Puducherry": (11.9416, 79.8083),
}

# Mandatory Prototype Disclaimer
DISCLAIMER = (
    "All hospital and availability information shown here is simulated demo data for prototype purposes."
)

EMERGENCY_MESSAGE = (
    "If this is a medical emergency, contact emergency services (108/112) or visit the nearest "
    "emergency department immediately. NexCare does not provide emergency treatment or ambulance booking."
)

NON_CHENNAI_NOTICE = (
    "Distances are calculated relative to your selected location."
)

STATE_HOSPITAL_NOTICE = ""

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance in kilometers between two points
    on the earth (specified in decimal degrees).
    """
    try:
        r = 6371.0  # Earth's radius in kilometers
        d_lat = math.radians(lat2 - lat1)
        d_lon = math.radians(lon2 - lon1)
        a = (
            math.sin(d_lat / 2) ** 2
            + math.cos(math.radians(lat1))
            * math.cos(math.radians(lat2))
            * math.sin(d_lon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return round(r * c, 1)
    except Exception:
        return 10.0
