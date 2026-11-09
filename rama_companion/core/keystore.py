import os
SERVICE = "RamaCompanion"

def _user(fid): return f"openai:{fid}"

def get_key(fid, fam_config=None):
    # 1. Check if we embedded it in the family JSON
    if fam_config and fam_config.get("api_key"):
        return fam_config["api_key"].strip()
        
    # 2. Check Windows Credential Manager
    try:
        import keyring
        k = keyring.get_password(SERVICE, f"openai:{fid}")
        if k: return k
    except Exception:
        pass
        
    # 3. Fallback to environment variable (developer convenience)
    return os.environ.get("OPENAI_API_KEY") or None

def set_key(fid, key):
    import keyring
    keyring.set_password(SERVICE, _user(fid), key.strip())

def clear_key(fid):
    try:
        import keyring
        keyring.delete_password(SERVICE, _user(fid))
    except Exception:
        pass
