from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from extensions.models import AbstractBaseModel
from extensions.models.mixins import SoftDeleteMixin
from users.managers import UserManager


class User(AbstractBaseUser, PermissionsMixin, SoftDeleteMixin, AbstractBaseModel):
    """
    The concrete user class that will be used in the database.

    By default, implements a `username` field, and `is_staff` and `is_active` status, alongside everything provided by
    the `BaseAbstractModel`.
    """

    username = models.CharField(unique=True, max_length=255)
    discord_id = models.CharField(unique=True, max_length=255, null=True, blank=True)

    is_active = models.BooleanField(
        default=True, help_text="Designates the user as active.", verbose_name="active status"
    )
    is_staff = models.BooleanField(
        default=False, help_text="Designates this user as a staff member.", verbose_name="staff status"
    )

    USERNAME_FIELD = "username"
    objects = UserManager()

    @classmethod
    def get_user_for_discord_id(cls, discord_id: str, discord_username: str) -> "User":
        """
        Get the corresponding User for the given Discord Id. If no User exists, create a new one with the Discord
        username.

        If a User with the same username already exists, this will cycle trough names (adding `_{counter}`) until the
        name is unique.
        """
        # We don't use get_or_create because we need to specifically call `create_user` on the manager.
        try:
            return cls.objects.get(discord_id=discord_id)
        except cls.DoesNotExist:
            if not cls.objects.filter(username=discord_username).exists():
                return cls.objects.create_user(username=discord_username, discord_id=discord_id)
            counter = 1
            username = discord_username + f"_{counter}"
            while cls.objects.filter(username=username).exists():
                counter += 1
                username = discord_username + f"_{counter}"
            return cls.objects.create_user(username=username, discord_id=discord_id)

    class Meta(AbstractBaseModel.Meta): ...

    def __str__(self) -> str:
        return f"User ({self.id}) {self.get_username()}"
