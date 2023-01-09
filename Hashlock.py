import smartpy as sp

class Hashlock(sp.Contract):
    def __init__(self, address):
        self.init(admin=address,
                  revealed=True,
                  amount=sp.tez(0),
                  reveal_time=sp.timestamp(0),
                  salted=sp.bytes('0x'),
                  receiver=sp.address("tz1YbCiXtXZ2HtXGecejTbbpww4GzFH7HvYQ")
                  )

    @sp.entry_point
    def commit(self, receiver, amount, hash):
        sp.verify_equal(sp.source, self.data.admin, message="You are not allowed to commit to this contract.")
        sp.verify(self.data.revealed == True, message="You cannot commit while the old hash is not revealed.")
        sp.verify(sp.amount >= amount, message="This contract does not own enough tz.")
        today = sp.now
        reveal_time = today.add_days(1)
        salted = hash + sp.pack(receiver)
        self.data.salted = sp.sha256(salted)
        self.data.reveal_time = reveal_time
        self.data.amount = amount
        self.data.revealed = False
        self.data.receiver = receiver

    @sp.entry_point
    def reveal(self, number):
        sp.verify(sp.now >= self.data.reveal_time, message="You cannot reveal unless 1 day has passed since commit.")
        sp.verify(self.data.revealed == False, message="Commit has already been revealed.")
        random_number = number
        bytes_random_number = sp.pack(random_number)
        hashedNumber = sp.sha256(bytes_random_number)
        salted = hashedNumber + sp.pack(sp.source)
        revealHash = sp.sha256(salted)
        sp.verify_equal(self.data.salted, revealHash, message = "Reveal did not match commit.")
        self.data.revealed = True
        sp.send(sp.source, self.data.amount, message="Address not found.")
        
    @sp.add_test(name="Hashlock1")
    def test():
        alice = sp.test_account("Alice")
        bob = sp.test_account("Bob")
        admin = sp.test_account("Administrator")
        r = Hashlock(admin.address)
        scenario = sp.test_scenario()
        scenario.h1("Contract Origination")
        scenario += r

        scenario.h2("Test 'commit' entrypoint")
        receiver = bob
        amount = sp.tez(10)
        random_number = sp.nat(345)
        bytes_random_number = sp.pack(random_number)
        hash = sp.sha256(bytes_random_number)
        
        scenario.h3("The authorized admin successfully calls commit")
        scenario += r.commit(receiver=receiver.address, amount=amount,
        hash=hash).run(source=admin.address, amount=sp.tez(10), now=sp.timestamp_from_utc_now())

        scenario.h3("The unauthorized user alice unsuccessfully calls commit")
        scenario += r.commit(receiver=receiver.address, amount=amount,
        hash=hash).run(source=alice.address, amount=sp.tez(10), now=sp.timestamp_from_utc_now(), valid=False)
    
        scenario.h3("The authorized admin can't commit twice without the receiver revealing first")
        scenario += r.commit(receiver=receiver.address, amount=amount,
        hash=hash).run(source=admin.address, amount=sp.tez(10), now=sp.timestamp_from_utc_now(), valid=False)

        scenario.h2("Test 'reveal' entrypoint")
        number = sp.nat(345)

        scenario.h3("The authorized receiver successfully calls reveal")
        scenario += r.reveal(number=number).run(source=bob.address, now=sp.timestamp_from_utc_now().add_days(2))

        scenario.h3("The authorized receiver unsuccessfully calls reveal twice")
        scenario += r.reveal(number=number).run(source=bob.address, now=sp.timestamp_from_utc_now().add_days(3), valid=False)

        scenario.h2("Test 'commit' again")

        scenario.h3("The authorized admin doesn't have enough tez to call commit")
        scenario += r.commit(receiver=receiver.address, amount=amount,
        hash=hash).run(source=admin.address, amount=sp.tez(5), now=sp.timestamp_from_utc_now(), valid=False)

        scenario.h3("The authorized admin successfully calls commit")
        scenario += r.commit(receiver=receiver.address, amount=amount,
        hash=hash).run(source=admin.address, amount=sp.tez(10), now=sp.timestamp_from_utc_now())

        scenario.h2("Test 'reveal' again")
        number = sp.nat(345)

        scenario.h3("The authorized receiver cannot reveal unless one day has passed")
        scenario += r.reveal(number=number).run(source=bob.address, now=sp.timestamp_from_utc_now(), valid=False)

        number = sp.nat(344)

        scenario.h3("Reveal did not match commit")
        scenario += r.reveal(number=number).run(source=bob.address, now=sp.timestamp_from_utc_now().add_days(2), valid=False)

        number = sp.nat(345)

        scenario.h3("The authorized receiver successfully calls reveal")
        scenario += r.reveal(number=number).run(source=bob.address, now=sp.timestamp_from_utc_now().add_days(2))
