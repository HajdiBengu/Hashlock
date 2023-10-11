import smartpy as sp

@sp.module
def main():
    class Hashlock(sp.Contract):
        def __init__(self, admin):
            self.data.sender = admin
            self.data.receiver = sp.address("0x")
            self.data.amount = sp.tez(0)
            self.data.saltedHash = sp.bytes('0x')
            self.data.revealed = True
            self.data.revealTime = sp.now
            
        @sp.entrypoint
        def commit(self, receiver, amount, hash):
            assert sp.sender == self.data.sender, "Not Admin"
            assert self.data.revealed == True, "Old Hash Not Revealed"
            assert sp.amount >= amount, "Not enough tez."
            self.data.revealed = False
            before = sp.now
            after = sp.add_seconds(before, 300)
            self.data.revealTime = after
            salted = hash + sp.pack(receiver)
            self.data.saltedHash = sp.sha256(salted)
            self.data.amount = amount
            self.data.receiver = receiver

        @sp.entrypoint
        def reveal(self, secretKey):
            assert sp.now >= self.data.revealTime, "5 mins need to pass"
            assert self.data.revealed == False, "Commit has been revealed"
            bytes_secret = sp.pack(secretKey)
            hashedNumber = sp.sha256(bytes_secret)
            salted = hashedNumber + sp.pack(sp.source)
            revealHash = sp.sha256(salted)
            assert self.data.saltedHash == revealHash, "Did not match"
            self.data.revealed = True
            sp.send(self.data.receiver, self.data.amount)
                
@sp.add_test(name = "Hashlock")
def test():
        alice = sp.test_account("Sender")
        bob = sp.test_account("Receiver")
        mallory = sp.test_account("Attacker")
    
        r = main.Hashlock(alice.address)
        s = sp.test_scenario(main)
        s.h1("Contract Origination")
        s += r

        secret_key = sp.nat(92018)
        bytes_secret_key = sp.pack(secret_key)
        hashInput = sp.sha256(bytes_secret_key)
        wrong_key = sp.nat(102018)
        amount = sp.tez(2)
        wrong_amount = sp.tez(1)

        s.h3("Admin doesn't have enough tez to commit")
        r.commit(receiver=bob.address, amount=amount, hash=hashInput).run(sender=alice.address, amount=wrong_amount, now=sp.timestamp_from_utc_now(), valid=False)

        s.h3("Admin successfully commits")
        r.commit(receiver=bob.address, amount=amount, hash=hashInput).run(source=alice.address, amount=amount, now=sp.timestamp_from_utc_now())

        s.h3("Attacker calls commit")
        r.commit(receiver=bob.address, amount=amount, hash=hashInput).run(sender=mallory.address, amount=amount, now=sp.timestamp_from_utc_now(), valid=False)

        s.h3("Admin calls commit twice")
        r.commit(receiver=bob.address, amount=amount, hash=hashInput).run(sender=admin.address, amount=amount, now=sp.timestamp_from_utc_now(), valid=False)

        s.h3("Receiver cannot reveal unless 5 minutes have passed")
        r.reveal(secret_key).run(sender=bob.address, now=sp.timestamp_from_utc_now(), valid=False)

        s.h3("Receiver calls reveal with the wrong secret key")
        r.reveal(wrong_key).run(source=bob.address, now=sp.timestamp_from_utc_now().add_seconds(400), valid=False)

        s.h3("Attacker calls reveal")
        r.reveal(secret_key).run(source=mallory.address, now=sp.timestamp_from_utc_now().add_seconds(400), valid=False)

        s.h3("Receiver successfully calls reveal")
        r.reveal(secret_key).run(source=bob.address, now=sp.timestamp_from_utc_now().add_seconds(400))

        s.h3("Receiver calls reveal twice")
        r.reveal(secret_key).run(sender=bob.address, now=sp.timestamp_from_utc_now().add_seconds(600), valid=False)
        
        s.h3("Admin successfully commits again")
        r.commit(receiver=bob.address, amount=amount, hash=hashInput).run(source=alice.address, amount=amount, now=sp.timestamp_from_utc_now())
