from typing import cast
from uuid import UUID
from django.urls import reverse
from rest_framework import status
from extensions.utilities import jsonify, uuid
from extensions.utilities.test import APITestCase
from realm_manager import models, serializers
from realm_manager.tests import sample_account, sample_game_world, sample_player
from users.tests import sample_user


class TestGameWorldViews(APITestCase):
    LIST_URL = reverse("realm_manager:game-world-list")

    def setUp(self) -> None:
        self.user = sample_user()
        self.client.force_authenticate(self.user)

    def test_get_game_world_list(self) -> None:
        """Test getting the GameWorld list."""
        # Create some sample data
        game_worlds = [sample_game_world() for _ in range(5)]
        # Make the call
        res = self.client.get(self.LIST_URL)
        # Verify the response
        self.assertResponseStatusCode(status.HTTP_200_OK, res)
        serialized_data = cast(list, jsonify(serializers.ListGameWorld(game_worlds, many=True).data))
        self.assertCountEqual(serialized_data, res.json())

    def test_get_auth(self) -> None:
        """Test that the GameWorld list endpoint is auth protected."""
        self.client.logout()
        # Make the call
        res = self.client.get(self.LIST_URL)
        # Verify the response
        self.assertResponseStatusCode(status.HTTP_401_UNAUTHORIZED, res)


class TestAccountViews(APITestCase):
    LIST_CREATE_URL = reverse("realm_manager:accounts:list-create")
    JOIN_URL = reverse("realm_manager:accounts:join")

    def DETAILS_URL(self, account_id: str | UUID) -> str:
        return reverse("realm_manager:accounts:details:base", kwargs={"pk": str(account_id)})

    def LEAVE_URL(self, account_id: str | UUID) -> str:
        return reverse("realm_manager:accounts:details:leave", kwargs={"pk": str(account_id)})

    def REMOVE_USER_URL(self, account_id: str | UUID, user_id: str | UUID) -> str:
        return reverse(
            "realm_manager:accounts:details:remove-user", kwargs={"pk": str(account_id), "user_id": str(user_id)}
        )

    def setUp(self) -> None:
        self.user = sample_user()
        self.client.force_authenticate(self.user)

    def test_get_account_list(self) -> None:
        """Test getting the Account list."""
        # Create some sample data
        accounts = [sample_account(owner=self.user) for _ in range(5)]
        # Make the call
        res = self.client.get(self.LIST_CREATE_URL)
        # Verify the response
        self.assertResponseStatusCode(status.HTTP_200_OK, res)
        serialized_data = cast(list, jsonify(serializers.ListCreateAccountSerializer(accounts, many=True).data))
        self.assertCountEqual(serialized_data, res.json())

    def test_get_auth(self) -> None:
        """Test that the Account list endpoint is auth protected."""
        self.client.logout()
        # Make the call
        res = self.client.get(self.LIST_CREATE_URL)
        # Verify the response
        self.assertResponseStatusCode(status.HTTP_401_UNAUTHORIZED, res)

    def test_get_filtered(self) -> None:
        """Test that getting the Account list only retrieves the Accounts for the correct user."""
        # Create some sample data
        other_user = sample_user()
        other_account = sample_account(owner=other_user)
        # Make the call
        res = self.client.get(self.LIST_CREATE_URL)
        # Verify the response
        self.assertResponseStatusCode(status.HTTP_200_OK, res)
        self.assertNotIn(serializers.ListCreateAccountSerializer(other_account).data, res.json())

    def test_create_account(self) -> None:
        """Test creating an Account."""
        original_count = models.Account.objects.count()
        # Make the call
        payload = {
            "name": "_name",
            "game_world": sample_game_world().id,
            "race": models.Account.Race.ELF,
            "economy": models.Account.Economy.MULTI_RES,
        }
        res = self.client.post(self.LIST_CREATE_URL, data=payload)
        # Verify the response
        self.assertResponseStatusCode(status.HTTP_201_CREATED, res)
        self.assertEqual(original_count + 1, models.Account.objects.count())
        created_account = models.Account.objects.get(id=res.data["id"])
        self.assertEqual(jsonify(serializers.ListCreateAccountSerializer(created_account).data), res.json())

    def test_create_account_multi_account_fails(self) -> None:
        """Test creating an Account on a GameWorld the user is already in fails."""
        game_world = sample_game_world()
        # Create an account for the user in the server before the call
        sample_account(owner=self.user, game_world=game_world)
        # Make the call
        payload = {
            "name": "_name",
            "game_world": game_world.id,
            "race": models.Account.Race.ELF,
            "economy": models.Account.Economy.MULTI_RES,
        }
        res = self.client.post(self.LIST_CREATE_URL, data=payload)
        # Verify the response
        self.assertResponseStatusCode(status.HTTP_400_BAD_REQUEST, res)
        self.assertEqual(
            {
                "type": "validation_error",
                "errors": [
                    {"code": "multi_account", "detail": "User is already present in this game world.", "attr": "user"}
                ],
            },
            res.json(),
        )

    def test_join_account(self) -> None:
        """Test joining an existing Account."""
        account = sample_account()
        # Make the call
        res = self.client.post(self.JOIN_URL, data={"id": account.id})
        # Verify the response
        self.assertResponseStatusCode(status.HTTP_201_CREATED, res)
        account.refresh_from_db()
        self.assertTrue(account.players.filter(user=self.user).exists())

    def test_join_not_found(self) -> None:
        """Test joining a non-existing Account fails with a 404."""
        # Make the call
        res = self.client.post(self.JOIN_URL, data={"id": uuid()})
        # Verify the response
        self.assertResponseStatusCode(status.HTTP_404_NOT_FOUND, res)

    def test_join_account_auth(self) -> None:
        """Test that the Account join endpoint is auth protected."""
        self.client.logout()
        # Make the call
        res = self.client.post(self.JOIN_URL, data={"id": sample_account().id})
        # Verify the response
        self.assertResponseStatusCode(status.HTTP_401_UNAUTHORIZED, res)

    def test_join_multi_account_fails(self) -> None:
        """Test joining an Account on a GameWorld the user is already in fails."""
        game_world = sample_game_world()
        account = sample_account(game_world=game_world)
        # Create an account for the user in the server before the call
        sample_account(owner=self.user, game_world=game_world)
        # Make the call
        res = self.client.post(self.JOIN_URL, data={"id": account.id})
        # Verify the response
        self.assertResponseStatusCode(status.HTTP_400_BAD_REQUEST, res)
        self.assertEqual(
            {
                "type": "validation_error",
                "errors": [
                    {"code": "multi_account", "detail": "User is already present in this game world.", "attr": "user"}
                ],
            },
            res.json(),
        )

    def test_get_account_as_owner(self) -> None:
        """Test retrieving a specific Account, when the user is the owner."""
        account = sample_account(owner=self.user)
        # Make the call
        res = self.client.get(self.DETAILS_URL(account.id))
        # Verify the response
        self.assertResponseStatusCode(status.HTTP_200_OK, res)
        self.assertEqual(jsonify(serializers.AccountDetailsSerializer(account).data), res.json())

    def test_get_account_as_player(self) -> None:
        """Test retrieving a specific Account, when the user is a player there."""
        account = sample_account()
        sample_player(user=self.user, account=account)
        # Make the call
        res = self.client.get(self.DETAILS_URL(account.id))
        # Verify the response
        self.assertResponseStatusCode(status.HTTP_200_OK, res)
        self.assertEqual(jsonify(serializers.AccountDetailsSerializer(account).data), res.json())

    def test_get_account_filtered(self) -> None:
        """Test that the user can only retrieve accounts that he's a part of."""
        account = sample_account()
        # Make the call
        res = self.client.get(self.DETAILS_URL(account.id))
        # Verify the response
        self.assertResponseStatusCode(status.HTTP_404_NOT_FOUND, res)

    def test_delete_account(self) -> None:
        """Test deleting an Account."""
        account = sample_account(owner=self.user)
        original_count = models.Account.objects.count()
        # Make the call
        res = self.client.delete(self.DETAILS_URL(account.id))
        # Verify the response
        self.assertResponseStatusCode(status.HTTP_204_NO_CONTENT, res)
        # Verify the database
        self.assertEqual(original_count - 1, models.Account.objects.count())
        self.assertFalse(models.Account.objects.filter(id=account.id).exists())

    def test_delete_account_not_owner_fails(self) -> None:
        """Test that deleting an Account while you're not the owner fails."""
        account = sample_account()
        sample_player(user=self.user, account=account)
        # Make the call
        res = self.client.delete(self.DETAILS_URL(account.id))
        # Verify the response
        self.assertResponseStatusCode(status.HTTP_403_FORBIDDEN, res)
        self.assertEqual(
            {
                "type": "client_error",
                "errors": [
                    {
                        "code": "permission_denied",
                        "detail": "You must be the account owner to perform this operation.",
                        "attr": "user",
                    }
                ],
            },
            res.json(),
        )

    def test_update_account_owner(self) -> None:
        """Test updating the Account's owner."""
        account = sample_account(owner=self.user)
        other_player = sample_player(account=account)
        # Make the call
        res = self.client.put(self.DETAILS_URL(account.id), data={"owner": other_player.user.id})
        # Verify the response
        self.assertResponseStatusCode(status.HTTP_200_OK, res)
        account.refresh_from_db()
        self.assertEqual(other_player.user, account.owner)

    def test_update_account_other_fails(self) -> None:
        """Test that only the Account's owner can be updated."""
        account = sample_account(owner=self.user)
        new_name = "_new_name"
        # Make the call
        res = self.client.put(self.DETAILS_URL(account.id), data={"name": new_name})
        # Verify the response
        self.assertResponseStatusCode(status.HTTP_400_BAD_REQUEST, res)
        account.refresh_from_db()
        self.assertNotEqual(new_name, account.name)

    def test_update_account_not_owner_fails(self) -> None:
        """Test that updating an Account while you're not the owner fails."""
        account = sample_account()
        sample_player(user=self.user, account=account)
        # Make the call
        res = self.client.put(self.DETAILS_URL(account.id), data={"owner": self.user.id})
        # Verify the response
        self.assertResponseStatusCode(status.HTTP_403_FORBIDDEN, res)
        self.assertEqual(
            {
                "type": "client_error",
                "errors": [
                    {
                        "code": "permission_denied",
                        "detail": "You must be the account owner to perform this operation.",
                        "attr": "user",
                    }
                ],
            },
            res.json(),
        )

    def test_update_account_owner_not_player_fails(self) -> None:
        """Test that updating an Account with a player that doesn't belong to it fails."""
        account = sample_account(owner=self.user)
        other_user = sample_user()
        # Make the call
        res = self.client.put(self.DETAILS_URL(account.id), data={"owner": other_user.id})
        # Verify the response
        self.assertResponseStatusCode(status.HTTP_400_BAD_REQUEST, res)
        self.assertEqual(
            {
                "type": "validation_error",
                "errors": [
                    {"code": "bad_owner", "detail": "The new owner is not a player in this account.", "attr": "owner"}
                ],
            },
            res.json(),
        )

    def test_update_account_owner_noop(self) -> None:
        """Test that updating the Account's owner to themselves does nothing."""
        account = sample_account(owner=self.user)
        # Make the call
        res = self.client.put(self.DETAILS_URL(account.id), data={"owner": self.user.id})
        # Verify the response
        self.assertResponseStatusCode(status.HTTP_200_OK, res)
        account.refresh_from_db()
        self.assertEqual(self.user, account.owner)

    def test_remove_user(self) -> None:
        """Test the endpoint to remove Users."""
        account = sample_account(owner=self.user)
        player = sample_player(account=account)
        account.refresh_from_db()
        original_count = account.players.count()
        # Make the call
        res = self.client.delete(self.REMOVE_USER_URL(account.id, player.user.id))
        # Verify the response
        self.assertResponseStatusCode(status.HTTP_204_NO_CONTENT, res)
        account.refresh_from_db()
        self.assertEqual(original_count - 1, account.players.count())
        self.assertFalse(account.players.filter(id=player.id).exists())

    def test_remove_user_not_owner_fails(self) -> None:
        """Test that only the owner of the Account can remove Users."""
        account = sample_account()
        player = sample_player(user=self.user, account=account)
        account.refresh_from_db()
        original_count = account.players.count()
        # Make the call
        res = self.client.delete(self.REMOVE_USER_URL(account.id, self.user.id))
        # Verify the response
        self.assertResponseStatusCode(status.HTTP_403_FORBIDDEN, res)
        self.assertEqual(
            {
                "type": "client_error",
                "errors": [
                    {
                        "code": "permission_denied",
                        "detail": "You must be the account owner to perform this operation.",
                        "attr": "user",
                    }
                ],
            },
            res.json(),
        )
        account.refresh_from_db()
        self.assertEqual(original_count, account.players.count())
        self.assertTrue(account.players.filter(id=player.id).exists())

    def test_remove_owner_fails(self) -> None:
        """Test that removing the owner of the Account fails."""
        account = sample_account(owner=self.user)
        original_count = account.players.count()
        # Make the call
        res = self.client.delete(self.REMOVE_USER_URL(account.id, self.user.id))
        # Verify the response
        self.assertResponseStatusCode(status.HTTP_400_BAD_REQUEST, res)
        account.refresh_from_db()
        self.assertEqual(original_count, account.players.count())
        self.assertTrue(account.players.filter(user=self.user).exists())
        self.assertEqual(
            {
                "type": "validation_error",
                "errors": [
                    {
                        "code": "failed_remove_owner",
                        "detail": "The owner of the account cannot be removed.",
                        "attr": "owner",
                    }
                ],
            },
            res.json(),
        )
