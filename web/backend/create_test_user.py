import asyncio
from database import get_users_collection
from auth_utils import hash_password

async def create_user():
    users = get_users_collection()
    email = "testtutor3@example.com"
    password = "password123"
    
    # Check if user already exists
    existing = await users.find_one({"email": email})
    if existing:
        print(f"User {email} already exists in database.")
        return
        
    hashed = hash_password(password)
    new_user = {
        "email": email,
        "hashed_password": hashed,
    }
    await users.insert_one(new_user)
    print(f"Successfully created user {email} in database!")

if __name__ == "__main__":
    asyncio.run(create_user())
