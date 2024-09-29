from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.db import transaction
from .models import TurfSlot, UserModel, SwimmingSlot, BadmintonSlot, SwimmingSession
import json
import logging
from datetime import datetime, time

logger = logging.getLogger(__name__)

class TurfSlotConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        logger.debug("WebSocket connection accepted.")

    async def disconnect(self, close_code):
        logger.debug("WebSocket connection closed.")

    async def receive(self, text_data):
        logger.debug(f"Received data: {text_data}")
        data = json.loads(text_data)
        
        message_type = data.get('type', None)
        sports = data.get('sports', None)

        if not sports:
            await self.send_error('Missing "sports" field.', is_available=True)
            return

        if message_type == 'get_available_sessions' and sports == 'Swimming':
            await self.handle_get_available_sessions(data)
        elif message_type == 'book_slot':
            await self.handle_book_slot(data)
        else:
            await self.send_error('Unsupported message type or missing parameters.', is_available=True)

    async def handle_book_slot(self, data):
        """
        Handle slot booking based on the sport type.
        """
        sports = data.get('sports')
        session_id = data.get('session_id')  # Ensure this key matches frontend
        turf_id = data.get('turf_id')
        field_size_id = data.get('field_size_id')
        start_time = data.get('start_time')
        end_time = data.get('end_time')
        date = data.get('date')
        user_id = data.get('user_id')
        number_of_people = data.get('number_of_people', 1)  # Default to 1 if not provided

        try:
            # Validate and create the slot based on the sport type
            if sports in ['Cricket', 'Football']:
                slot_id, message, is_booked, is_available = await self.create_turf_slot(
                    user_id=user_id,
                    turf_id=turf_id,
                    field_size_id=field_size_id,
                    sports=sports,
                    start_time=start_time,
                    end_time=end_time,
                    date=date,
                )
            elif sports == 'Swimming':
                slot_id, message, is_booked, is_available = await self.create_swimming_slot(
                    user_id=user_id,
                    turf_id=turf_id,
                    field_size_id=field_size_id,
                    session_id=session_id,  # Ensure this matches
                    date=date,
                    number_of_people=number_of_people,
                )
            elif sports == 'Badminton':
                slot_id, message, is_booked, is_available = await self.create_badminton_slot(
                    user_id=user_id,
                    turf_id=turf_id,
                    field_size_id=field_size_id,
                    start_time=start_time,
                    end_time=end_time,
                    date=date,
                )
            else:
                raise ValueError(f"Unsupported sport: {sports}")

            # Send a message back with the booking status
            await self.send(text_data=json.dumps({
                'message': message,
                'slot_id': slot_id,
                'isBooked': is_booked,
                'isAvailable': is_available,
            }))
        except Exception as e:
            logger.error(f"Error booking slot: {e}")
            await self.send(text_data=json.dumps({
                'message': f'Error booking slot: {str(e)}. Please try again.',
                'isBooked': False,
                'isAvailable': True
            }))
    @database_sync_to_async
    def create_turf_slot(self, user_id, turf_id, field_size_id, sports, start_time, end_time, date):
        """
        Create a turf slot for Cricket or Football.
        """
        # Convert string date and times to datetime objects for comparison
        start_datetime = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M")
        end_datetime = datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %H:%M")
        current_datetime = datetime.now()

        # Step 1: Validate start and end times
        if start_datetime >= end_datetime:
            return None, 'Start time must be earlier than end time.', False, True

        # Step 2: Validate that the date is in the future
        if start_datetime < current_datetime:
            return None, 'Cannot book a slot in the past. Please select a future date and time.', False, True

        # Step 3: Check for existing slots at the same time
        overlapping_slot = TurfSlot.objects.filter(
            turf_id=turf_id,
            field_size_id=field_size_id,
            sports=sports,  # Ensure sports is correctly used
            date=date,
            start_time__lt=end_time,
            end_time__gt=start_time,
            is_available=True,
        ).exists()

        if overlapping_slot:
            return None, 'The selected slot is already booked. Please choose a different time.', True, False

        user = UserModel.objects.get(id=user_id)
        turf_slot = TurfSlot.objects.create(
            user=user,
            turf_id=turf_id,
            sports=sports,
            field_size_id=field_size_id,
            start_time=start_time,
            end_time=end_time,
            date=date,
            is_available=False, 
        )
        return turf_slot.id, 'Slot booked successfully.', True, False

    @database_sync_to_async
    def create_swimming_slot(self, user_id, turf_id, field_size_id, session_id, date, number_of_people):
        """
        Create a swimming slot.
        """
        # Validate number_of_people
        try:
            number_of_people = int(number_of_people)
            if number_of_people <= 0:
                raise ValueError("Number of people must be greater than zero.")
        except ValueError:
            logger.debug(f"Invalid number_of_people: {number_of_people}")
            return None, 'Invalid number of people. Please enter a valid number.', False, True

        try:
            session = SwimmingSession.objects.get(id=session_id)
            logger.debug(f"Found SwimmingSession: ID={session.id}, Start={session.start_time}, End={session.end_time}")
        except SwimmingSession.DoesNotExist:
            logger.debug(f"SwimmingSession with ID={session_id} does not exist.")
            return None, 'Selected swimming session does not exist.', False, True

        # Check if the date is valid (ensure date is today or in the future)
        try:
            session_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            logger.debug(f"Invalid date format: {date}")
            return None, "Invalid date format. Expected 'YYYY-MM-DD'.", False, True

        if session_date < datetime.today().date():
            logger.debug(f"Attempted to book a session in the past: {session_date}")
            return None, 'Cannot book a slot in the past. Please select a future date.', False, True

        # Check remaining capacity
        remaining_capacity = session.remaining_capacity(session_date)
        logger.debug(f"Remaining capacity for session ID={session.id} on {session_date}: {remaining_capacity}")

        if remaining_capacity < number_of_people:
            logger.debug(f"Not enough capacity: Requested={number_of_people}, Available={remaining_capacity}")
            return None, f'Only {remaining_capacity} spots are available for this session.', False, False

        with transaction.atomic():
            # Re-fetch the session with a lock to prevent race conditions
            session = SwimmingSession.objects.select_for_update().get(id=session_id)
            remaining_capacity = session.remaining_capacity(session_date)
            logger.debug(f"Locked SwimmingSession: ID={session.id}, Remaining Capacity={remaining_capacity}")

            if remaining_capacity < number_of_people:
                logger.debug("Cannot book. Slot capacity exceeded after locking.")
                raise ValueError("Cannot book. Slot capacity exceeded.")

            # Create the SwimmingSlot
            user = UserModel.objects.get(id=user_id)
            swimming_slot = SwimmingSlot.objects.create(
                user=user,
                turf_id=turf_id,
                field_size_id=field_size_id,
                session=session,
                date=session_date,
                number_of_people=number_of_people,
            )
            logger.debug(f"Created SwimmingSlot: ID={swimming_slot.id}, User={user.id}, People={number_of_people}")

        return swimming_slot.id, 'Swimming slot booked successfully.', True, True

    @database_sync_to_async
    def create_badminton_slot(self, user_id, turf_id, field_size_id, start_time, end_time, date):
        """
        Create a badminton slot.
        """
        # Convert string date and times to datetime objects for comparison
        start_datetime = datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M")
        end_datetime = datetime.strptime(f"{date} {end_time}", "%Y-%m-%d %H:%M")
        current_datetime = datetime.now()

        if start_datetime >= end_datetime:
            return None, 'Start time must be earlier than end time.', False, True

        if start_datetime < current_datetime:
            return None, 'Cannot book a slot in the past. Please select a future date and time.', False, True

        # Check for existing slots at the same time
        overlapping_slot = BadmintonSlot.objects.filter(
            turf_id=turf_id,
            field_size_id=field_size_id,
            date=date,
            start_time__lt=end_time,
            end_time__gt=start_time,
            is_available=True,
        ).exists()

        if overlapping_slot:
            return None, 'The selected slot is already booked. Please choose a different time.', True, False

        user = UserModel.objects.get(id=user_id)
        badminton_slot = BadmintonSlot.objects.create(
            user=user,
            turf_id=turf_id,
            field_size_id=field_size_id,
            start_time=start_time,
            end_time=end_time,
            date=date,
            is_available=False, 
        )
        return badminton_slot.id, 'Slot booked successfully.', True, False

    @database_sync_to_async
    def get_available_swimming_sessions(self, date):
        """
        Retrieve available swimming sessions for a given date.
        """
        try:
            session_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("Invalid date format. Expected 'YYYY-MM-DD'.")

        sessions = SwimmingSession.objects.all()
        available_sessions = []

        for session in sessions:
            remaining_capacity = session.remaining_capacity(session_date)
            if remaining_capacity > 0:
                available_sessions.append({
                    'session_id': session.id,
                    'start_time': session.start_time.strftime("%H:%M"),
                    'end_time': session.end_time.strftime("%H:%M"),
                    'remaining_capacity': remaining_capacity,
                    'price_per_person': float(session.price_per_person),
                })

        return available_sessions

    async def handle_get_available_sessions(self, data):
        """
        Handle the retrieval of available swimming sessions.
        """
        date = data.get('date', None)
        if not date:
            await self.send_error('Missing "date" field.', is_available=False)
            return

        try:
            available_sessions = await self.get_available_swimming_sessions(date)
            await self.send(text_data=json.dumps({
                'type': 'available_sessions',
                'sessions': available_sessions
            }))
        except Exception as e:
            logger.error(f"Error fetching available sessions: {e}")
            await self.send_error('Error fetching available sessions.', is_available=False)

    async def send_error(self, message, is_available=True):
        """
        Send an error message back to the client.
        """
        await self.send(text_data=json.dumps({
            'message': f'Error: {message}',
            'isBooked': False,
            'isAvailable': is_available
        }))
