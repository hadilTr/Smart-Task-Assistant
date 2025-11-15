"""
Test if server.py can start without errors
"""
import os
import sys
from dotenv import load_dotenv

print("🔍 Testing server.py startup...")
print("=" * 50)

# Load env
load_dotenv()

# Test 1: Environment variables
print("\n1️⃣ Checking environment variables...")
mongo_uri = os.getenv("MONGO_URI")
if mongo_uri:
    print(f"✅ MONGO_URI: {mongo_uri[:30]}...")
else:
    print("❌ MONGO_URI not found!")
    sys.exit(1)

# Test 2: MongoDB connection
print("\n2️⃣ Testing MongoDB connection...")
try:
    from pymongo import MongoClient
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    print("✅ MongoDB connection OK")
    client.close()
except Exception as e:
    print(f"❌ MongoDB connection FAILED: {e}")
    sys.exit(1)

# Test 3: Import server module
print("\n3️⃣ Testing server.py imports...")
try:
    # Add backend to path if needed
    backend_path = os.path.join(os.path.dirname(__file__), 'backend')
    if os.path.exists(backend_path):
        sys.path.insert(0, backend_path)
    
    # Try importing the server
    import importlib.util
    server_path = os.path.join(backend_path if os.path.exists(backend_path) else '.', 'server.py')
    
    if not os.path.exists(server_path):
        server_path = 'server.py'
    
    print(f"   Loading from: {server_path}")
    
    spec = importlib.util.spec_from_file_location("server_test", server_path)
    server_module = importlib.util.module_from_spec(spec)
    
    # This will execute the module and catch any initialization errors
    spec.loader.exec_module(server_module)
    
    print("✅ Server imports successfully")
    print(f"✅ FastMCP server created: {server_module.server.name}")
    
except Exception as e:
    print(f"❌ Server import FAILED: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 50)
print("✅ ALL CHECKS PASSED!")
print("\nThe server can initialize successfully.")
print("The client error must be something else.")
print("\nTry running the fixed client1.py now.")