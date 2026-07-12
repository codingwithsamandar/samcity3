# Mahalla (neighborhood) chat olib tashlandi: ChatRoom/ChatMessage/ChatMember/
# MessageReaction modellari o'chiriladi. ChatAdmin (mahalla admini roli) SAQLANADI.
#
# Faqat DeleteModel ishlatiladi (RemoveField emas) — SQLite'da RemoveField
# jadvalni qayta quradi va o'chirilayotgan maydonga bog'langan indeks
# (chat_msg_room_created_idx) tufayli xato beradi. DeleteModel esa DROP TABLE
# qiladi (indekslar jadval bilan birga o'chadi). Tartib: bog'liqlar avval.
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0028_adcampaign_send_to_all'),
    ]

    operations = [
        migrations.DeleteModel(name='MessageReaction'),  # FK -> ChatMessage
        migrations.DeleteModel(name='ChatMember'),       # FK -> ChatRoom
        migrations.DeleteModel(name='ChatMessage'),      # FK -> ChatRoom (+ self)
        migrations.DeleteModel(name='ChatRoom'),         # FK -> Neighborhood
    ]
