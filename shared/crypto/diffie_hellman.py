import secrets


class DiffieHellman:
    P = int("FFFFFFFFFFFFFFFFC90FDAA22168C234C4C6628B80DC1CD129024E088A67CC74020BBEA63B139B22514A08798E3404DDEF9519B3CD3A431B302B0A6DF25E14374FE1356D6D51C245E485B576625E7EC6F44C42E9A637ED6B0BFF5CB6F406B7EDEE386BFB5A899FA5AE9F24117C4B1FE649286651ECE45B3DC2007CB8A163BF0598DA48361C55D39A69163FA8FD24CF5F83655D23DCA3AD961C62F356208552BB9FD529077096966D670C354E4ABC9804F1746C08CA237327FFFFFFFFFFFFFFFF",
        16
    )

    G = 2

    def __init__(self):
        self.private_key = secrets.randbelow(self.P - 3) + 2
        self.public_key = pow(self.G, self.private_key, self.P)

    def compute_shared_secret(self, peer_public_key: int) -> int:
        if not 2 <= peer_public_key <= self.P - 2:
            raise ValueError("Invalid peer public key")

        return pow(peer_public_key, self.private_key, self.P)
