from datetime import datetime
from unittest.mock import MagicMock, patch
from django.utils.timezone import make_aware
from core.extensions.models import BaseAbstractModel
from core.utilities.test import AbstractModelTestCase


class TestBaseAbstractModel(AbstractModelTestCase):
    class ConcreteModel(BaseAbstractModel):
        ...

    MODEL = ConcreteModel

    # Utility functions
    def sample_object(self) -> ConcreteModel:
        return self.ConcreteModel.objects.create()

    @patch("django.utils.timezone.now")
    def test_create(self, timezone_mock: MagicMock) -> None:
        """Test creation of a BaseAbstractModel object."""
        # Setup the mock
        dt_created = make_aware(datetime(1970, 1, 1))
        dt_updated = make_aware(datetime(1970, 1, 2))
        timezone_mock.side_effect = [dt_created, dt_updated]
        # Create the object
        obj = self.sample_object()
        self.assertTrue(obj.id)  # Not empty
        self.assertEqual(dt_created, obj.created_at)
        self.assertEqual(dt_updated, obj.updated_at)
        self.assertFalse(obj.is_deleted)
        # Test the __repr__ while we're at it
        self.assertEqual(
            str(
                {
                    "model": self.ConcreteModel.__name__,
                    "id": obj.id,
                    "created_at": obj.created_at,
                    "updated_at": obj.updated_at,
                    "is_deleted": obj.is_deleted,
                }
            ),
            repr(obj),
        )

    @patch("django.utils.timezone.now")
    def test_soft_delete(self, timezone_mock: MagicMock) -> None:
        """Test the `soft_delete` method."""
        # Setup the mock
        dt_original = make_aware(datetime(1970, 1, 1))
        dt_updated = make_aware(datetime(1970, 1, 2))
        timezone_mock.side_effect = [dt_original, dt_original, dt_updated]
        # Create the object
        obj = self.sample_object()
        # Make sure the `updated_at` is not our mock yet and it's not deleted
        self.assertEqual(dt_original, obj.updated_at)
        self.assertFalse(obj.is_deleted)
        # Soft delete it
        obj.soft_delete()
        self.assertEqual(dt_updated, obj.updated_at)
        self.assertTrue(obj.is_deleted)
