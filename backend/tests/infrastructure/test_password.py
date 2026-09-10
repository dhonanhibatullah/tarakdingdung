from tarakdingdung.infrastructure.utility.password.bcrypt import BcryptPassword


def test_hash_and_verify_roundtrip():
    p = BcryptPassword(cost=4)
    hashed = p.hash("secret")
    assert hashed != "secret"
    assert p.verify("secret", hashed)


def test_verify_rejects_wrong_password():
    p = BcryptPassword(cost=4)
    hashed = p.hash("secret")
    assert not p.verify("wrong", hashed)


def test_verify_rejects_malformed_hash():
    p = BcryptPassword(cost=4)
    assert not p.verify("secret", "not-a-bcrypt-hash")
