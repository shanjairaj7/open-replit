# User model without UserRole - should trigger attribute error
class User:
    def __init__(self, username: str):
        self.username = username
    
    def get_name(self):
        return self.username

# Note: UserRole is NOT defined here