class UsersService:

    def create_batches(users, num_processes): 

        if len(users) == 0:
            return users
        
        batch_size = max(1, len(users) // num_processes)
        
        if len(users) % num_processes != 0:
            batch_size += 1
        
        batches = []
        total = 0
        for i in range(0, len(users), batch_size):
            batches.append(users[i:i + batch_size])
            total+=batch_size

        return batches