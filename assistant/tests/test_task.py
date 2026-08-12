"""task.py testlari — AgentTask holat mashinasi (slot to'ldirish, muddat)."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from .. import task as task_mod
from ..models import AgentTask
from . import _fixtures


def _mk_user(phone):
    return get_user_model().objects.create_user(phone=phone, password='x')


class TaskLifecycleTests(TestCase):
    def setUp(self):
        self.user = _mk_user('998902000001')
        self.ctx = _fixtures.user_ctx(self.user)

    def test_create_and_reuse_active(self):
        t1 = task_mod.get_or_create_active(self.ctx, 'order', missing=['store_id', 'product_id'])
        t2 = task_mod.get_or_create_active(self.ctx, 'order')
        self.assertEqual(t1.id, t2.id)  # bir xil faol vazifa

    def test_set_slot_removes_from_missing(self):
        t = task_mod.get_or_create_active(self.ctx, 'order', missing=['store_id', 'product_id'])
        task_mod.set_slot(t, 'store_id', 12)
        t.refresh_from_db()
        self.assertEqual(t.slots['store_id'], 12)
        self.assertNotIn('store_id', t.missing)
        self.assertEqual(task_mod.next_missing(t), 'product_id')

    def test_ready_when_no_missing(self):
        t = task_mod.get_or_create_active(self.ctx, 'order', missing=['store_id'])
        self.assertFalse(task_mod.is_ready(t))
        task_mod.set_slot(t, 'store_id', 5)
        self.assertTrue(task_mod.is_ready(t))

    def test_complete(self):
        t = task_mod.get_or_create_active(self.ctx, 'order')
        task_mod.complete(t)
        t.refresh_from_db()
        self.assertEqual(t.status, 'done')

    def test_expired_active_becomes_abandoned(self):
        t = task_mod.get_or_create_active(self.ctx, 'order')
        AgentTask.objects.filter(pk=t.pk).update(
            expires_at=timezone.now() - timezone.timedelta(hours=1))
        # active_task muddati o'tganini abandoned qiladi va None qaytaradi
        self.assertIsNone(task_mod.active_task(self.ctx, goal='order'))
        t.refresh_from_db()
        self.assertEqual(t.status, 'abandoned')


class AnonTaskTests(TestCase):
    def test_session_scoped_task(self):
        ctx = _fixtures.anon_ctx(session_key='sess-abc')
        t1 = task_mod.get_or_create_active(ctx, 'order')
        t2 = task_mod.get_or_create_active(ctx, 'order')
        self.assertEqual(t1.id, t2.id)
        # Boshqa sessiya — boshqa vazifa
        ctx2 = _fixtures.anon_ctx(session_key='sess-xyz')
        t3 = task_mod.get_or_create_active(ctx2, 'order')
        self.assertNotEqual(t1.id, t3.id)
