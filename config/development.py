documents_per_page = 10

app_secret_key = "myZ@perK3y"

session_cookie_name = "_sandbox_app_sid"
session_expiration_time = 86400 * 7 * 2  # 2 weeks
token_expiration_time = 86400 * 7 * 2  # 2 weeks

token_auto_prolongation = True

pymongo_extra = {
    "serverSelectionTimeoutMS": 1100,
    "socketTimeoutMS": 1100,
    "connectTimeoutMS": 1100,
}

database = {
    "meta": {
        "uri": "mongodb://localhost",
        "pymongo_extra": pymongo_extra,
        "dbname": "sandboxapp_meta_dev",
    },
    "shards": {
        "s1": {
            "uri": "mongodb://localhost",
            "pymongo_extra": pymongo_extra,
            "dbname": "sandboxapp_s1_dev",
        },
        "s2": {
            "uri": "mongodb://localhost",
            "pymongo_extra": pymongo_extra,
            "dbname": "sandboxapp_s2_dev",
        },
    }
}

log_level = "debug"
log_format = "[%(asctime)s] %(levelname)s\t%(module)-8.8s:%(lineno)-3d %(message)s"
