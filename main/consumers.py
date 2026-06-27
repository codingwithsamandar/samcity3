import json
import base64
import uuid
import re
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.cache import cache
from django.utils import timezone
from django.core.files.base import ContentFile

MENTION_RE = re.compile(r'@([A-Za-z0-9_]{2,50})')
ONLINE_TTL = 60 * 10  # presence cache TTL (seconds)
MAX_MEDIA_BYTES = 8 * 1024 * 1024  # 8 MB per voice/file/image over WS


def _online_key(room_id):
    return f'chat_online_{room_id}'


class ChatConsumer(AsyncWebsocketConsumer):
    """Advanced Mahalla chat: messages, media, reply, edit, soft-delete,
    reactions, @mentions, typing, presence/last-seen and read receipts."""

    # ── Connection lifecycle ──────────────────────────────────────
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close()
            return

        room = await self.get_room()
        if not room:
            await self.close()
            return

        self.is_chat_admin = await self.check_is_admin()
        self.is_approved = await self.ensure_member()
        self.is_banned = await self.check_is_banned()

        if self.is_banned and not self.is_chat_admin:
            await self.accept()
            await self.send(text_data=json.dumps({'type': 'banned', 'text': 'Siz bu chatdan bloklangansiz.'}))
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        await self.send(text_data=json.dumps({
            'type': 'status',
            'is_admin': self.is_chat_admin,
            'is_approved': self.is_approved,
            'is_banned': self.is_banned,
            'me': str(self.user.id),
        }))

        # ── Presence: mark online, broadcast join, send snapshot ──
        await self._set_online(True)
        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'presence', 'user_id': str(self.user.id), 'online': True, 'last_seen': '',
        })
        await self.send(text_data=json.dumps({'type': 'online_list', 'users': self._online_users()}))

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self._set_online(False)
            last_seen = await self.touch_last_seen()
            await self.channel_layer.group_send(self.room_group_name, {
                'type': 'presence', 'user_id': str(self.user.id), 'online': False, 'last_seen': last_seen,
            })
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    # ── Inbound message router ────────────────────────────────────
    async def receive(self, text_data):
        data = json.loads(text_data)
        t = data.get('type', 'message')
        can_write = self.is_chat_admin or self.is_approved

        if t == 'message':
            if not can_write:
                return await self._err("Yozish uchun admin tasdig'ini kuting.")
            text = (data.get('text') or '').strip()
            if not text or len(text) > 4000:
                return
            msg = await self.save_message(text, reply_to_id=data.get('reply_to'))
            await self._broadcast_message(msg)
            await self._handle_mentions(text, msg['id'])

        elif t in ('image_message', 'file_message', 'voice_message'):
            if not can_write:
                return await self._err("Yozish uchun admin tasdig'ini kuting.")
            kind = {'image_message': 'image', 'file_message': 'file', 'voice_message': 'audio'}[t]
            msg = await self.save_media(
                kind, data.get('data', ''), (data.get('caption') or '').strip()[:500],
                data.get('filename', ''), reply_to_id=data.get('reply_to'),
            )
            if not msg:
                return await self._err("Fayl yuklashda xatolik.")
            await self._broadcast_message(msg)

        elif t == 'edit_message':
            text = (data.get('text') or '').strip()
            if text:
                ok = await self.edit_message(data.get('message_id'), text)
                if ok:
                    await self.channel_layer.group_send(self.room_group_name, {
                        'type': 'message_edited', 'message_id': str(data.get('message_id')), 'text': text,
                    })

        elif t == 'delete_message':
            ok = await self.soft_delete(data.get('message_id'))
            if ok:
                await self.channel_layer.group_send(self.room_group_name, {
                    'type': 'message_deleted', 'message_id': str(data.get('message_id')),
                })

        elif t == 'reaction':
            if not can_write:
                return
            counts = await self.toggle_reaction(data.get('message_id'), data.get('emoji', ''))
            if counts is not None:
                await self.channel_layer.group_send(self.room_group_name, {
                    'type': 'reaction_update', 'message_id': str(data.get('message_id')), 'reactions': counts,
                })

        elif t == 'forward':
            if not can_write:
                return
            msg = await self.forward_message(data.get('message_id'))
            if msg:
                await self._broadcast_message(msg)

        elif t == 'mark_read':
            ts = await self.mark_read()
            await self.channel_layer.group_send(self.room_group_name, {
                'type': 'read_receipt', 'user_id': str(self.user.id), 'at': ts,
            })

        elif t == 'typing':
            if not can_write:
                return
            display_name = '🛡️ Admin' if self.is_chat_admin else (self.user.name or self.user.phone)
            await self.channel_layer.group_send(self.room_group_name, {
                'type': 'user_typing', 'user_name': display_name,
                'user_id': 'admin' if self.is_chat_admin else str(self.user.id),
                'is_typing': data.get('is_typing', False),
            })

        elif t == 'kick_user' and self.is_chat_admin:
            uid = data.get('user_id')
            if uid:
                await self.ban_member(uid)
                await self.channel_layer.group_send(self.room_group_name, {
                    'type': 'user_kicked', 'user_id': uid, 'text': 'Foydalanuvchi chatdan chiqarildi.',
                })

        elif t == 'approve_member' and self.is_chat_admin:
            uid = data.get('user_id')
            if uid:
                await self.approve_member(uid)
                await self.channel_layer.group_send(self.room_group_name, {
                    'type': 'member_approved', 'user_id': uid,
                })

    async def _err(self, text):
        await self.send(text_data=json.dumps({'type': 'error', 'text': text}))

    async def _broadcast_message(self, msg):
        display_name = '🛡️ Admin' if self.is_chat_admin else (self.user.name or self.user.phone)
        display_initials = 'AD' if self.is_chat_admin else self.get_initials()
        display_user_id = 'admin' if self.is_chat_admin else str(self.user.id)
        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'chat_message',
            'message': {
                **msg,
                'user_id': display_user_id,
                'real_user_id': str(self.user.id),
                'user_name': display_name,
                'user_initials': display_initials,
                'is_admin': self.is_chat_admin,
            },
        })

    async def _handle_mentions(self, text, message_id):
        usernames = set(MENTION_RE.findall(text or ''))
        if usernames:
            await self.notify_mentions(list(usernames), text)

    # ── Group event handlers ──────────────────────────────────────
    async def chat_message(self, event):
        m = event['message']
        await self.send(text_data=json.dumps({
            'type': 'message',
            'is_own': m.get('real_user_id') == str(self.user.id),
            'can_delete': self.is_chat_admin or m.get('real_user_id') == str(self.user.id),
            'can_edit': m.get('real_user_id') == str(self.user.id) and m.get('kind') == 'text',
            **m,
        }))

    async def message_edited(self, event):
        await self.send(text_data=json.dumps({'type': 'message_edited', 'message_id': event['message_id'], 'text': event['text']}))

    async def message_deleted(self, event):
        await self.send(text_data=json.dumps({'type': 'message_deleted', 'message_id': event['message_id']}))

    async def reaction_update(self, event):
        await self.send(text_data=json.dumps({'type': 'reaction_update', 'message_id': event['message_id'], 'reactions': event['reactions']}))

    async def read_receipt(self, event):
        if event['user_id'] != str(self.user.id):
            await self.send(text_data=json.dumps({'type': 'read_receipt', 'user_id': event['user_id'], 'at': event['at']}))

    async def presence(self, event):
        if event['user_id'] != str(self.user.id):
            await self.send(text_data=json.dumps({
                'type': 'presence', 'user_id': event['user_id'],
                'online': event['online'], 'last_seen': event.get('last_seen', ''),
            }))

    async def user_typing(self, event):
        if event.get('user_id') != ('admin' if self.is_chat_admin else str(self.user.id)):
            await self.send(text_data=json.dumps({'type': 'typing', 'user_name': event['user_name'], 'is_typing': event['is_typing']}))

    async def user_kicked(self, event):
        if str(self.user.id) == event.get('user_id'):
            self.is_banned = True
            await self.send(text_data=json.dumps({'type': 'banned', 'text': event.get('text', 'Siz chatdan chiqarildingiz.')}))
        elif self.is_chat_admin:
            await self.send(text_data=json.dumps({'type': 'system', 'text': "Foydalanuvchi chatdan chiqarildi."}))

    async def member_approved(self, event):
        if str(self.user.id) == event.get('user_id'):
            self.is_approved = True
            await self.send(text_data=json.dumps({'type': 'approved', 'text': 'Admin sizni tasdiqladi! Endi yoza olasiz.'}))

    # ── Presence cache (sync-safe via cache) ──────────────────────
    async def _set_online(self, online):
        await database_sync_to_async(self._cache_presence)(online)

    def _cache_presence(self, online):
        key = _online_key(self.room_id)
        data = cache.get(key) or {}
        if online:
            data[str(self.user.id)] = (self.user.name or self.user.phone)
        else:
            data.pop(str(self.user.id), None)
        cache.set(key, data, ONLINE_TTL)

    def _online_users(self):
        return list((cache.get(_online_key(self.room_id)) or {}).keys())

    # ── DB operations ─────────────────────────────────────────────
    @database_sync_to_async
    def get_room(self):
        from .models import ChatRoom
        try:
            return ChatRoom.objects.get(pk=self.room_id)
        except ChatRoom.DoesNotExist:
            return None

    @database_sync_to_async
    def check_is_admin(self):
        from .models import ChatRoom, ChatAdmin
        try:
            room = ChatRoom.objects.select_related('neighborhood').get(pk=self.room_id)
            return ChatAdmin.objects.filter(neighborhood=room.neighborhood, user=self.user).exists()
        except Exception:
            return False

    @database_sync_to_async
    def ensure_member(self):
        from .models import ChatRoom, ChatMember
        try:
            room = ChatRoom.objects.get(pk=self.room_id)
            member, _ = ChatMember.objects.get_or_create(
                room=room, user=self.user, defaults={'is_approved': False, 'is_banned': False})
            return member.is_approved
        except Exception:
            return False

    @database_sync_to_async
    def check_is_banned(self):
        from .models import ChatRoom, ChatMember
        try:
            room = ChatRoom.objects.get(pk=self.room_id)
            return ChatMember.objects.filter(room=room, user=self.user, is_banned=True).exists()
        except Exception:
            return False

    @database_sync_to_async
    def touch_last_seen(self):
        from .models import ChatMember
        now = timezone.now()
        ChatMember.objects.filter(room_id=self.room_id, user=self.user).update(last_seen_at=now)
        return timezone.localtime(now).strftime('%H:%M %d.%m')

    @database_sync_to_async
    def mark_read(self):
        from .models import ChatMember
        now = timezone.now()
        ChatMember.objects.filter(room_id=self.room_id, user=self.user).update(last_read_at=now, last_seen_at=now)
        return timezone.localtime(now).strftime('%H:%M')

    def _serialize(self, msg):
        from .models import ChatRoom  # noqa
        kind = 'text'
        if msg.image:
            kind = 'image'
        elif msg.audio:
            kind = 'audio'
        elif msg.file:
            kind = 'file'
        reply = None
        if msg.reply_to_id and msg.reply_to and not msg.reply_to.is_deleted:
            r = msg.reply_to
            reply = {
                'id': str(r.pk),
                'text': (r.text or ('📷 Rasm' if r.image else ('🎤 Ovozli xabar' if r.audio else ('📎 Fayl' if r.file else '')))) [:120],
                'author': '🛡️ Admin' if r.is_admin_message else (r.user.name or r.user.phone),
            }
        return {
            'id': str(msg.pk),
            'kind': kind,
            'text': msg.text or '',
            'image_url': msg.image.url if msg.image else None,
            'file_url': msg.file.url if msg.file else None,
            'file_name': (msg.file.name.split('/')[-1] if msg.file else None),
            'audio_url': msg.audio.url if msg.audio else None,
            'time': timezone.localtime(msg.created_at).strftime('%H:%M'),
            'reply': reply,
            'edited': bool(msg.edited_at),
            'forwarded': bool(msg.forwarded_from_id),
        }

    @database_sync_to_async
    def save_message(self, text, reply_to_id=None):
        from .models import ChatRoom, ChatMessage
        room = ChatRoom.objects.get(pk=self.room_id)
        reply = ChatMessage.objects.filter(pk=reply_to_id, room=room).first() if reply_to_id else None
        msg = ChatMessage.objects.create(
            room=room, user=self.user, text=text,
            is_admin_message=self.is_chat_admin, reply_to=reply,
        )
        msg.reply_to = reply  # ensure relation loaded
        return self._serialize(msg)

    @database_sync_to_async
    def save_media(self, kind, b64, caption, filename, reply_to_id=None):
        from .models import ChatRoom, ChatMessage
        try:
            raw = b64.split(',', 1)[1] if ',' in b64 else b64
            blob = base64.b64decode(raw)
            if not blob or len(blob) > MAX_MEDIA_BYTES:
                return None
            ext = {'image': 'jpg', 'audio': 'webm', 'file': (filename.split('.')[-1][:8] if '.' in filename else 'bin')}[kind]
            safe = f'chat_{uuid.uuid4().hex[:12]}.{ext}'
            cf = ContentFile(blob, name=safe)
            room = ChatRoom.objects.get(pk=self.room_id)
            reply = ChatMessage.objects.filter(pk=reply_to_id, room=room).first() if reply_to_id else None
            fields = {'room': room, 'user': self.user, 'text': caption,
                      'is_admin_message': self.is_chat_admin, 'reply_to': reply}
            if kind == 'image':
                fields['image'] = cf
            elif kind == 'audio':
                fields['audio'] = cf
            else:
                cf.name = (filename or safe)[:80]
                fields['file'] = cf
            msg = ChatMessage.objects.create(**fields)
            return self._serialize(msg)
        except Exception:
            return None

    @database_sync_to_async
    def edit_message(self, msg_id, text):
        from .models import ChatMessage
        try:
            msg = ChatMessage.objects.get(pk=msg_id, room_id=self.room_id)
            if msg.user_id != self.user.id and not self.is_chat_admin:
                return False
            msg.text = text[:4000]
            msg.edited_at = timezone.now()
            msg.save(update_fields=['text', 'edited_at'])
            return True
        except (ChatMessage.DoesNotExist, ValueError, TypeError):
            return False

    @database_sync_to_async
    def soft_delete(self, msg_id):
        from .models import ChatMessage
        try:
            msg = ChatMessage.objects.get(pk=msg_id, room_id=self.room_id)
            if msg.user_id != self.user.id and not self.is_chat_admin:
                return False
            msg.is_deleted = True
            msg.text = ''
            msg.save(update_fields=['is_deleted', 'text'])
            return True
        except (ChatMessage.DoesNotExist, ValueError, TypeError):
            return False

    @database_sync_to_async
    def toggle_reaction(self, msg_id, emoji):
        from .models import ChatMessage, MessageReaction
        emoji = (emoji or '')[:8]
        if not emoji:
            return None
        try:
            msg = ChatMessage.objects.get(pk=msg_id, room_id=self.room_id)
        except (ChatMessage.DoesNotExist, ValueError, TypeError):
            return None
        existing = MessageReaction.objects.filter(message=msg, user=self.user, emoji=emoji).first()
        if existing:
            existing.delete()
        else:
            MessageReaction.objects.create(message=msg, user=self.user, emoji=emoji)
        counts = {}
        for r in MessageReaction.objects.filter(message=msg):
            counts[r.emoji] = counts.get(r.emoji, 0) + 1
        return counts

    @database_sync_to_async
    def forward_message(self, msg_id):
        from .models import ChatRoom, ChatMessage, ChatMember
        try:
            src = ChatMessage.objects.get(pk=msg_id)
        except (ChatMessage.DoesNotExist, ValueError, TypeError):
            return None
        # IDOR himoyasi: foydalanuvchi faqat o'zi a'zo bo'lgan (yoki joriy)
        # xonadagi xabarni uzata oladi — begona xonadan ma'lumot oqib chiqmaydi.
        if str(src.room_id) != str(self.room_id):
            allowed = ChatMember.objects.filter(
                room_id=src.room_id, user=self.user, is_approved=True, is_banned=False
            ).exists()
            if not allowed:
                return None
        room = ChatRoom.objects.get(pk=self.room_id)
        msg = ChatMessage.objects.create(
            room=room, user=self.user, text=src.text,
            image=src.image or None, file=src.file or None, audio=src.audio or None,
            is_admin_message=self.is_chat_admin, forwarded_from=src,
        )
        return self._serialize(msg)

    @database_sync_to_async
    def notify_mentions(self, usernames, text):
        from .models import User, ChatRoom
        try:
            from notifications.models import notify
            from django.urls import reverse
            room = ChatRoom.objects.select_related('neighborhood').get(pk=self.room_id)
            url = reverse('neighborhood_chat_room', args=[room.id])
            users = User.objects.filter(username__in=usernames).exclude(id=self.user.id)
            for u in users:
                notify(u, f"Sizni eslatishdi: {text[:60]}", url, 'chat')
        except Exception:
            pass

    @database_sync_to_async
    def ban_member(self, user_id):
        from .models import ChatRoom, ChatMember
        try:
            room = ChatRoom.objects.get(pk=self.room_id)
            ChatMember.objects.filter(room=room, user__id=user_id).update(is_banned=True, is_approved=False)
        except Exception:
            pass

    @database_sync_to_async
    def approve_member(self, user_id):
        from .models import ChatRoom, ChatMember
        try:
            room = ChatRoom.objects.get(pk=self.room_id)
            ChatMember.objects.filter(room=room, user__id=user_id).update(
                is_approved=True, is_banned=False, approved_at=timezone.now())
        except Exception:
            pass

    def get_initials(self):
        name = self.user.name or self.user.phone
        parts = name.split()
        if len(parts) >= 2:
            return (parts[0][0] + parts[1][0]).upper()
        return name[:2].upper()
