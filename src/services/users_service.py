class UsersService:

    @staticmethod
    def create_batches(users, num_processes):

        if len(users) == 0:
            return users

        sorted_users = sorted(users)

        # Start with one empty list for each process.
        batches = []
        for _ in range(num_processes):
            batches.append([])

        # Distribute users in round-robin order.
        # This guarantees each batch gets an equal mix of heavy and light users.
        i = 0
        for user in sorted_users:
            target_batch = i % num_processes
            batches[target_batch].append(user)
            i += 1

        return batches
