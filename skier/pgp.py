#import json
#import multiprocessing

#import redis

#from cfg import cfg, redis_host
from flask.ext.sqlalchemy_cache import FromCache

from skier import keyinfo
from app import cache
import db


#cache = redis.StrictRedis(host=redis_host,
#                          port=cfg.config.redis.port,
#                          db=cfg.config.redis.db)


def add_pgp_key(armored: str) -> tuple:
    """
    Adds a key to the database.
    :param armored: The armored key data to add to the keyring.
    :return: True and the keyid if the import succeeded, or:
            False and -1 if it was invalid, False and -2 if it already existed or False and -3 if it's a private key.
    """
    if "PGP PRIVATE" in armored:
        return False, -3

    # Dump the key data.
    newkey = keyinfo.KeyInfo.pgp_dump(armored)
    # You tried, pgpdump. And that's more than we could ever ask of you.
    if not newkey:
        return False, -1

    # Put the data into the database.
    # Show me on the doll where redis touched you.
    exists = db.Key.query.filter(db.Key.key_fp_id == newkey.shortid).first()
    if exists:
        if exists.armored == armored:
            return False, -2
        else:
            use_id = exists.id
    else:
        use_id = None

    key = db.Key.from_keyinfo(newkey)
    key.armored = armored
    if use_id:
        key.id = use_id
    db.db.session.merge(key)
    db.db.session.commit()
    return True, newkey.shortid


def get_pgp_armor_key(keyid: str):
    """
    Lookup a PGP key.
    :param keyid: The key ID to lookup.
    :return: The armored version of the PGP key, or None if the key does not exist in the DB.
    """
    key = db.Key.query.options(FromCache(cache)).filter(db.Key.key_fp_id == keyid).first()
    if key: return key.armored
    else: return None

def get_pgp_keyinfo(keyid: str):
    """
    Gets a :skier.keyinfo.KeyInfo: object for the specified key.
    :param keyid: The ID of the key to lookup.
    :return: A new :skier.keyinfo.KeyInfo: object for the key.
    """
    key = db.Key.query.options(FromCache(cache)).filter(db.Key.key_fp_id == keyid).first()
    if key:
        return keyinfo.KeyInfo.pgp_dump(armored=key.armored)


def search_through_keys(search_str: str, page: int=1, count: int=10):
    """
    Searches through the keys via ID or UID name.
    :param search_str: The string to search for.
    Examples: '0xBF864998CDEEC2D390162087EB4084E3BF0192D9' for a fingerprint search
              '0x45407604' for a key ID search
              'Smith' for a name search
    :return: A list of :skier.keyinfo.KeyInfo: objects containing the specified keys.
    """
    if search_str.startswith("0x"):
        search_str = search_str.replace("0x", "")
        results = db.Key.query.options(FromCache(cache)).filter(db.Key.key_fp_id == search_str).paginate(page, per_page=count)
    else:
        results = db.Key.query.options(FromCache(cache)).filter(db.Key.uid.ilike("%{}%".format(search_str))).paginate(page, per_page=count)
    return results