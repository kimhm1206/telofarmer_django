import hashlib

def sha256_hash(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

# 사용 예시
plain_text = "kmelonpassword"
hashed_text = sha256_hash(plain_text)
print(hashed_text)


# 40c2a16b96fbcf3bbae440a9fdf5be4ffbb622bd8b6b4983e39044cfcee126db