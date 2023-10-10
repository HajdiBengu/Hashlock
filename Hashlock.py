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
        admin = sp.test_account("Administrator")
        alice = sp.test_account("Alice")
        bob = sp.test_account("Bob")
        r = main.Hashlock(admin.address)
        s = sp.test_scenario(main)
        s.h1("Contract Origination")
        s += r

        random_number = sp.nat(345)
        bytes_random_number = sp.pack(random_number)
        hashInput = sp.sha256(bytes_random_number)
        amount = sp.tez(2)

        s.h3("The authorized admin successfully calls commit")
        r.commit(receiver=bob.address, amount=amount, hash=hashInput).run(sender=admin.address, amount=sp.tez(2), now=sp.timestamp_from_utc_now())

        s.h3("The unauthorized user alice unsuccessfully calls commit")
        r.commit(receiver=bob.address, amount=amount, hash=hashInput).run(sender=alice.address, amount=sp.tez(2), now=sp.timestamp_from_utc_now(), valid=False)
    
        s.h3("The authorized admin can't commit twice without the receiver revealing first")
        r.commit(receiver=bob.address, amount=amount, hash=hashInput).run(sender=admin.address, amount=sp.tez(2), now=sp.timestamp_from_utc_now(), valid=False)

        s.h2("Test 'reveal' entrypoint")
        number = sp.nat(345)

        s.h3("The authorized receiver successfully calls reveal")
        r.reveal(number).run(sender=bob.address, now=sp.timestamp_from_utc_now().add_seconds(400))

        s.h3("The authorized receiver unsuccessfully calls reveal twice")
        r.reveal(number).run(sender=bob.address, now=sp.timestamp_from_utc_now().add_seconds(600), valid=False)

        s.h2("Test 'commit' again")

        s.h3("The authorized admin doesn't have enough tez to call commit")
        r.commit(receiver=bob.address, amount=amount, hash=hashInput).run(sender=admin.address, amount=sp.tez(1), now=sp.timestamp_from_utc_now(), valid=False)

        s.h3("The authorized admin successfully calls commit")
        r.commit(receiver=bob.address, amount=amount, hash=hashInput).run(sender=admin.address, amount=sp.tez(2), now=sp.timestamp_from_utc_now())

        s.h2("Test 'reveal' again")
        number = sp.nat(345)

        s.h3("The authorized receiver cannot reveal unless 5 minutes have passed")
        r.reveal(number).run(sender=bob.address, now=sp.timestamp_from_utc_now(), valid=False)

        number = sp.nat(344)

        s.h3("Reveal did not match commit")
        r.reveal(number).run(sender=bob.address, now=sp.timestamp_from_utc_now().add_seconds(400), valid=False)

        number = sp.nat(345)

        s.h3("The authorized receiver successfully calls reveal")
        r.reveal(number).run(sender=bob.address, now=sp.timestamp_from_utc_now().add_seconds(400))
