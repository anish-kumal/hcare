import json

from channels.generic.websocket import AsyncWebsocketConsumer


class DoctorSlotsConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.doctor_id = self.scope['url_route']['kwargs']['doctor_id']
        self.group_name = f'doctor_slots_{self.doctor_id}'

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        # Keep the socket alive; currently server-only push.
        pass

    async def slots_updated(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    'type': 'slots.updated',
                    'doctor_id': event['doctor_id'],
                }
            )
        )
