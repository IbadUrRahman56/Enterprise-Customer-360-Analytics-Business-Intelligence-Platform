"""Environment-backed local accounts. Production deployments should use an OIDC proxy."""
import hashlib
import hmac
import json
import os
import secrets

ROLES={"viewer","analyst","admin"}


def hash_password(password, salt=None):
    salt=salt or secrets.token_hex(16)
    value=hashlib.pbkdf2_hmac("sha256",password.encode(),salt.encode(),600000).hex()
    return f"pbkdf2_sha256$600000${salt}${value}"


def verify(password,encoded):
    try:
        method,iterations,salt,expected=encoded.split("$")
        if method!="pbkdf2_sha256" or not 100000<=int(iterations)<=2000000: return False
        got=hashlib.pbkdf2_hmac("sha256",password.encode(),salt.encode(),int(iterations)).hex()
        return hmac.compare_digest(got,expected)
    except (ValueError,TypeError): return False


def authenticate(username,password):
    accounts=json.loads(os.environ.get("C360_USERS_JSON","{}"))
    account=accounts.get(username,{})
    if account.get("role") not in ROLES: return None
    return account["role"] if verify(password,account.get("password_hash","")) else None


def allowed(role,action):
    return role in ({"admin","analyst"} if action=="export" else {"admin"} if action=="quality" else ROLES)
