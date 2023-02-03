from typing import Self
from users.abstract_models import BaseAbstractUser, UserEmailMixin, UserUsernameMixin
from users.managers import UserManager


class User(UserEmailMixin, UserUsernameMixin, BaseAbstractUser):
    """
    The concrete user class that will be used in the database.

    By default, implements both a `username` and an `email` field, using the `username` as the model's
    `USERNAME_FIELD`.

    This class can be customized by removing or adding other Mixins. For example, to only have a `username` and no
    email, remove the `UserEmailMixin` from the class' parents and the `REQUIRE_EMAIL` property. **Every change that
    modifies the resulting model requires a new migration.**

    See the mixins in `abstract_models.py` for more information.
    """

    objects = UserManager[Self]()  # type: ignore # https://github.com/python/mypy/issues/14167
    USERNAME_FIELD = "username"
    REQUIRE_EMAIL = True

    class Meta(BaseAbstractUser.Meta):
        ...

    def __str__(self) -> str:
        return f"User ({self.id}) {self.get_username()}"
