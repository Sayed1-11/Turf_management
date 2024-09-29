import requests
from django.conf import settings


def send_otp(mobile, otp):
    url = "http://bulksmsbd.net/api/smsapi"
    message = f"MangoIT OTP is {otp}"
    payload = {
        "api_key": settings.SMS_API_KEY,
        "senderid": "8809617620100",  # Update with your actual sender ID
        "number": mobile,
        "message": message
    }
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
    }
    
    response = requests.get(url, data=payload, headers=headers)
    return bool(response.ok)
