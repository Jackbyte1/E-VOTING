import secrets

from Crypto.PublicKey import RSA


def _one_line_pem(pem: bytes) -> str:
    return pem.decode("utf-8").replace("\n", "\\n")


def main() -> None:
    key = RSA.generate(2048)
    print("SECRET_KEY=" + secrets.token_urlsafe(48))
    print("VOTE_ENCRYPTION_KEY=" + secrets.token_urlsafe(32)[:32])
    print("VOTE_RSA_PRIVATE_KEY=" + _one_line_pem(key.export_key("PEM")))
    print("VOTE_RSA_PUBLIC_KEY=" + _one_line_pem(key.publickey().export_key("PEM")))


if __name__ == "__main__":
    main()
