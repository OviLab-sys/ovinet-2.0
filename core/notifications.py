from utils import send_templated_email

class NotificationService:
    @staticmethod
    def send_email(subject, template, ctx, recipients):
        send_templated_email(subject, template, ctx, recipients)


    @staticmethod
    def send_sms(phone_number, message):
        # integrate an SMS gateway or Mpesa utils
        raise NotImplementedError