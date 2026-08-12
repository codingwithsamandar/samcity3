"""community bo'limi — mahalla e'lonlari, murojaat, so'rovnoma + ovoz."""

from django.contrib.auth import get_user_model
from django.test import TestCase

from .. import confirm, registry
from . import _fixtures


def _mk_user(phone, neighborhood=None):
    u = get_user_model().objects.create_user(phone=phone, password='x', name='T')
    if neighborhood is not None:
        u.neighborhood = neighborhood
        u.save(update_fields=['neighborhood'])
    return u


class CommunitySetup(TestCase):
    def setUp(self):
        from main.models import District, Neighborhood
        self.district = District.objects.create(name='Shofirkon tumani')
        self.nb = Neighborhood.objects.create(name='Navoiy mahallasi', district=self.district)
        self.user = _mk_user('998919000001', self.nb)
        self.ctx = _fixtures.user_ctx(self.user, session_key='comm')


class AnnouncementsTests(CommunitySetup):
    def test_shows_neighborhood_and_district(self):
        from main.models import DistrictAnnouncement, NeighborhoodAnnouncement
        NeighborhoodAnnouncement.objects.create(neighborhood=self.nb,
                                                title='Suv o\'chadi', text='Ertaga')
        DistrictAnnouncement.objects.create(district=self.district,
                                            title='Tuman yig\'ilishi', text='...')
        res = registry.dispatch('community', 'announcements', {}, self.ctx)
        titles = [it['title'] for it in res['ui']['items']]
        self.assertIn('Suv o\'chadi', titles)
        self.assertIn('Tuman yig\'ilishi', titles)

    def test_no_neighborhood(self):
        user = _mk_user('998919000002')          # mahallasiz
        res = registry.dispatch('community', 'announcements', {},
                                _fixtures.user_ctx(user, session_key='x'))
        self.assertIn('mahalla tanlanmagan', res['speech'].lower())

    def test_empty(self):
        res = registry.dispatch('community', 'announcements', {}, self.ctx)
        self.assertIn('yo\'q', res['speech'].lower())


class SubmitRequestTests(CommunitySetup):
    def test_submit_flow_creates_request(self):
        from main.models import CitizenRequest
        res = registry.dispatch('community', 'submit_request', {
            'category': 'water', 'title': 'Suv yo\'q',
            'text': 'Uch kundan beri suv kelmayapti'}, self.ctx)
        self.assertEqual(res['result_status'], 'pending')
        self.assertEqual(res['ui']['type'], 'confirm')
        self.assertEqual(CitizenRequest.objects.count(), 0)
        confirm.execute(res['pending_id'], self.user)
        self.assertEqual(CitizenRequest.objects.filter(user=self.user).count(), 1)
        req = CitizenRequest.objects.get(user=self.user)
        self.assertEqual(req.category, 'water')
        self.assertEqual(req.neighborhood, self.nb)
        self.assertEqual(req.status, 'submitted')

    def test_anonymous_cannot_submit(self):
        res = registry.dispatch('community', 'submit_request',
                                {'category': 'road', 'title': 'X', 'text': 'Y'},
                                _fixtures.anon_ctx())
        self.assertEqual(res['result_status'], 'denied')


class PollVoteTests(CommunitySetup):
    def setUp(self):
        super().setUp()
        from main.models import Poll, PollOption
        self.poll = Poll.objects.create(creator=self.user, neighborhood=self.nb,
                                        question='Yangi park kerakmi?', is_active=True)
        self.opt_a = PollOption.objects.create(poll=self.poll, text='Ha', order=1)
        self.opt_b = PollOption.objects.create(poll=self.poll, text="Yo'q", order=2)

    def test_list_polls(self):
        res = registry.dispatch('community', 'list_polls', {}, self.ctx)
        self.assertEqual(res['ui']['type'], 'card_list')
        self.assertIn('Ha', [it['title'] for it in res['ui']['items']])

    def test_vote_flow(self):
        from main.models import PollVote
        res = registry.dispatch('community', 'vote',
                                {'poll_option_id': str(self.opt_a.pk)}, self.ctx)
        self.assertEqual(res['result_status'], 'pending')
        confirm.execute(res['pending_id'], self.user)
        self.assertEqual(PollVote.objects.filter(option=self.opt_a, user=self.user).count(), 1)

    def test_vote_accepts_prefixed_id(self):
        from main.models import PollVote
        res = registry.dispatch('community', 'vote',
                                {'poll_option_id': f'polloption:{self.opt_a.pk}'}, self.ctx)
        confirm.execute(res['pending_id'], self.user)
        self.assertTrue(PollVote.objects.filter(option=self.opt_a, user=self.user).exists())

    def test_single_poll_revote_replaces(self):
        from main.models import PollVote
        for opt in (self.opt_a, self.opt_b):
            res = registry.dispatch('community', 'vote',
                                    {'poll_option_id': str(opt.pk)}, self.ctx)
            confirm.execute(res['pending_id'], self.user)
        # single-type: faqat oxirgi ovoz qoladi
        self.assertEqual(PollVote.objects.filter(option__poll=self.poll, user=self.user).count(), 1)
        self.assertTrue(PollVote.objects.filter(option=self.opt_b, user=self.user).exists())
