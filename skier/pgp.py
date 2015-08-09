import redis

from app import gpg

from cfg import cfg

cache = redis.StrictRedis(host=cfg.config.redis.host,
                          port=cfg.config.redis.port,
                          db=cfg.config.redis.db)

def has_pgp_key(keyid: str):
    """
    Lookup an EXISTS on the Redis cache.
    :param keyid: The keyid to lookup.
    :return: If the key exists or not in the cache.
    """
    return True if cache.exists(keyid) == 1 else False

def get_pgp_key(keyid: str):
    """
    Lookup a PGP key on the redis cache.

    If the key does not exist in the cache, it will try and find it from the GPG keyring.
    :param keyid: The key ID to lookup.
    :return: The binary version of the PGP key, or None if the key does not exist in either the cache or the keyring.
    """
    if has_pgp_key(keyid):
        key = cache.get(keyid)
        return key
    else:
        # Try and look it up in the keyring.
        key = gpg.export_keys(keyid, armor=False)
        if key:
            # Add it to the cache.
            cache.set(keyid, key)
            cache.set(keyid + "-armor", gpg.export_keys(keyid, armor=True))
            return key
        else:
            return None

def get_pgp_armor_key(keyid:str):
    """
    Lookup a PGP key.

    If the key does not exist in the cache, it will try and find it from the GPG keyring.
    :param keyid: The key ID to lookup.
    :return: The armored version of the PGP key, or None if the key does not exist in either the cache or the keyring.
    """
    if has_pgp_key(keyid + "-armor"):
        key = cache.get(keyid + "-armor")
        return key.decode()
    else:
        # Try and look it up in the keyring.
        key = gpg.export_keys(keyid, armor=True)
        if key:
            # Add it to the cache.
            cache.set(keyid + "-armor", key)
            cache.set(keyid, gpg.export_keys(keyid, armor=False))
            return key
        else:
            return None

def invalidate_cache_key(keyid: str):
    """
    Invalidate a key on the cache (delete it) so it can be updated.
    :param keyid: The key to delete.
    :return: If the key was deleted or not.
    """
    if has_pgp_key(keyid):
        cache.delete([keyid, keyid + "-armor"])
    else:
        return False